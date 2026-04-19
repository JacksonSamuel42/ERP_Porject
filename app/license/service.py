import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import GRACE_PERIOD_DAYS, MAX_OFFLINE_DAYS
from app.auth.models import ClientProfile, ClientUser, PartnerProfile, User
from app.license.config import license_settings
from app.license.exceptions import (
    LicenseNotFoundException,
    MaxMachinesReachedException,
    PartnerClientLimitReachedException,
    PartnerNotAuthorizedException,
)
from app.license.models import ClientLicense, LicensePeriod, PartnerLicense
from app.license.utils import LicenseCrypto, calculate_expiration, generate_partner_key
from app.plan.exceptions import (
    ERPPlanNotFoundException,
    PartnerPlanNotFoundException,
    PlanLimitExceededException,
)
from app.plan.models import ERPPlan, PartnerPlan
from app.user.exceptions import UserClientNotFoundException, UserPartnerNotFoundException


class LicenseService:
    @staticmethod
    async def get_client_license(session: AsyncSession, user: User) -> Optional[ClientLicense]:
        """Lógica exclusiva para buscar licença de Clientes e seus utilizadores."""
        client_id = await LicenseService.get_client_id_from_user(session, user.id)

        if not client_id:
            return None

        stmt = (
            select(ClientLicense)
            .where(ClientLicense.client_id == client_id)
            .where(ClientLicense.is_active)
            .order_by(desc(ClientLicense.expiry_date))
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_partner_license(session: AsyncSession, user: User) -> Optional[PartnerLicense]:
        """Lógica exclusiva para buscar a licença do próprio Parceiro."""
        # Busca o perfil do parceiro primeiro
        partner_stmt = select(PartnerProfile).where(PartnerProfile.user_id == user.id)
        partner_res = await session.execute(partner_stmt)
        partner = partner_res.scalar_one_or_none()

        if not partner:
            return None

        stmt = (
            select(PartnerLicense)
            .where(PartnerLicense.partner_id == partner.id)
            .where(PartnerLicense.is_active)
            .order_by(desc(PartnerLicense.expiry_date))
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_client_id_from_user(session: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        """Helper para encontrar o client_id seja dono ou funcionário."""
        # Tenta funcionário
        res = await session.execute(
            select(ClientUser.client_id).where(ClientUser.user_id == user_id)
        )
        client_id = res.scalar()

        # Se não for, tenta dono
        if not client_id:
            res = await session.execute(
                select(ClientProfile.id).where(ClientProfile.user_id == user_id)
            )
            client_id = res.scalar()

        return client_id

    @staticmethod
    async def is_license_valid(session: AsyncSession, client_id: uuid.UUID) -> bool:
        """Verifica se a licença existe, está ativa e não expirou."""
        stmt = select(ClientLicense).where(
            ClientLicense.client_id == client_id,
            ClientLicense.is_active,
            ClientLicense.expiry_date >= datetime.now(timezone.utc),
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None

    # ---------- Partner Licensing ----------

    @staticmethod
    async def assign_license_to_partner(
        session: AsyncSession,
        partner_id: uuid.UUID,
        partner_plan_id: uuid.UUID,
        period: LicensePeriod,
    ) -> PartnerLicense:
        """
        Atribui licença ao parceiro com expiração automática e chave gerada.
        """
        start_date = datetime.now(timezone.utc)
        expiry_date = calculate_expiration(start_date, period)
        generated_key = generate_partner_key()

        partner = await session.get(PartnerProfile, partner_id)
        partner_plan = await session.get(PartnerPlan, partner_plan_id)

        if not partner:
            raise UserPartnerNotFoundException()
        if not partner_plan:
            raise PartnerPlanNotFoundException()

        new_lic = PartnerLicense(
            partner_id=partner_id,
            partner_plan_id=partner_plan_id,
            start_date=start_date,
            expiry_date=expiry_date,
            period=period,
            license_key=generated_key,
            is_active=True,
        )

        session.add(new_lic)
        try:
            await session.commit()
            await session.refresh(new_lic)
            return new_lic
        except Exception as e:
            await session.rollback()
            raise e

    # ---------- Client Licensing (The Core Logic) ----------

    @staticmethod
    async def emit_client_license(
        session: AsyncSession,
        user_id: uuid.UUID,
        client_id: uuid.UUID,
        erp_plan_id: uuid.UUID,
        expiry_date: datetime,
        period: LicensePeriod,
        offline_only: bool = False,
    ) -> ClientLicense:
        """
        Emite uma licença para um cliente, validando regras e gerando a chave RSA.
        """
        result = await session.execute(
            select(PartnerProfile).where(PartnerProfile.user_id == user_id)
        )
        partner = result.scalar_one_or_none()
        partner_id = partner.id

        client = await session.get(ClientProfile, client_id)
        erp_plan = await session.get(ERPPlan, erp_plan_id)

        if not client:
            raise UserClientNotFoundException()
        if not erp_plan:
            raise ERPPlanNotFoundException()

        # Verificar se o Parceiro tem uma licença ativa e válida
        partner_lic_stmt = select(PartnerLicense).where(
            PartnerLicense.partner_id == partner_id,
            PartnerLicense.is_active,
            PartnerLicense.expiry_date >= datetime.now(timezone.utc),
        )
        result = await session.execute(partner_lic_stmt)
        partner_lic = result.scalar_one_or_none()

        if not partner_lic:
            raise PlanLimitExceededException('Partner License Inactive or Expired')

        # Buscar as regras do plano do Parceiro e o ERPPlan pretendido
        partner_plan_result = await session.execute(
            select(PartnerPlan).where(PartnerPlan.id == partner_lic.partner_plan_id)
        )
        p_plan = partner_plan_result.scalar_one_or_none()

        erp_plan_result = await session.execute(select(ERPPlan).where(ERPPlan.id == erp_plan_id))
        erp_plan = erp_plan_result.scalar_one_or_none()

        if not erp_plan:
            raise ERPPlanNotFoundException()

        # Validar se o Parceiro pode revender este ERPPlan
        allowed_plans = p_plan.allowed_erp_plans
        if str(erp_plan_id) not in allowed_plans:
            raise PartnerNotAuthorizedException()

        # 4. Validar limite de quantidade de clientes do Parceiro
        client_count_stmt = select(func.count(ClientProfile.id)).where(
            ClientProfile.partner_id == partner_id
        )
        count_res = await session.execute(client_count_stmt)
        if p_plan.is_at_limit(count_res.scalar()):
            raise PartnerClientLimitReachedException()

        start_date = datetime.now(timezone.utc)
        expiry_date = calculate_expiration(start_date, period)

        # Preparar os dados para a Assinatura Digital (Payload Offline)
        license_data = {
            'version': '1.0',
            'client_id': str(client_id),
            'plan_name': erp_plan.name,
            'modules': erp_plan.modules_enabled,
            'ranges': erp_plan.plan_ranges,
            'offline_only': offline_only,
            'max_machines': erp_plan.default_max_machines,
            'iat': start_date.isoformat(),
            'exp': expiry_date.isoformat(),
        }

        # Gerar a Assinatura RSA
        private_key_pem = license_settings.RSA_PRIVATE_KEY

        # O método sign_license_data retorna o JSON bundle com a signature
        signed_license_key = LicenseCrypto.sign_license_data(
            data=license_data, private_key_pem=private_key_pem.encode('utf-8')
        )

        metadata = {
            'issued_at': datetime.now(timezone.utc).isoformat(),
            'grace_expiration_days': GRACE_PERIOD_DAYS,
            'status': 'active',
            'origin': 'backend_api',
        }

        if not offline_only:
            metadata['max_offline_days'] = MAX_OFFLINE_DAYS

        # Criar e persistir a licença no banco
        new_client_lic = ClientLicense(
            client_id=client_id,
            partner_id=partner_id,
            erp_plan_id=erp_plan_id,
            expiry_date=expiry_date,
            period=period,
            offline_only=offline_only,
            license_key=signed_license_key,
            license_metadata=metadata,
            authorized_machines=[],
        )

        session.add(new_client_lic)
        try:
            await session.commit()
            await session.refresh(new_client_lic)
            return new_client_lic
        except Exception as e:
            await session.rollback()
            raise e

    @staticmethod
    async def activate_client_machine(
        session: AsyncSession, client_id: uuid.UUID, machine_id: str
    ) -> ClientLicense:
        """
        Adiciona um hardware ID à licença sem perder os dados do plano original.
        """
        stmt = (
            select(ClientLicense, ERPPlan)
            .join(ERPPlan, ClientLicense.plan_id == ERPPlan.id)
            .where(
                ClientLicense.client_id == client_id,
                ClientLicense.is_active,
                ClientLicense.expiry_date >= datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        row = result.first()

        if not row:
            raise LicenseNotFoundException()

        license, erp_plan = row

        # Verificar se a máquina já está lá ou se há espaço
        if machine_id not in license.authorized_machines:
            if len(license.authorized_machines) >= erp_plan.default_max_machines:
                raise MaxMachinesReachedException()

            new_machines = list(license.authorized_machines)
            new_machines.append(machine_id)
            license.authorized_machines = new_machines

        # RECONSTRUIR o payload completo (Mantendo o que foi definido na emissão)
        full_license_data = {
            'version': '1.0',
            'client_id': str(license.client_id),
            'plan_name': erp_plan.name,
            'modules': erp_plan.modules_enabled,
            'ranges': erp_plan.plan_ranges,
            'max_machines': erp_plan.default_max_machines,
            'machines': license.authorized_machines,
            'iat': int(datetime.now(timezone.utc).timestamp()),
            'exp': int(license.expiry_date.timestamp()),
        }

        # Assinar o novo conjunto completo de dados
        private_key_pem = license_settings.RSA_PRIVATE_KEY
        license.license_key = LicenseCrypto.sign_license_data(
            data=full_license_data, private_key_pem=private_key_pem.encode('utf-8')
        )

        try:
            await session.commit()
            await session.refresh(license)
            return license
        except Exception as e:
            await session.rollback()
            raise e

    @staticmethod
    async def my_license():
        pass
