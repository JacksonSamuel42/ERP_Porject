import uuid
from datetime import datetime, timezone
from typing import Tuple

from fastapi import BackgroundTasks
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import (
    EmailUsernameOrPasswordException,
    InactiveUserException,
    LicenseExpiredException,
    PartnerAccessExpiredException,
    ProfileNotFoundException,
)
from app.auth.models import (
    ClientProfile,
    ClientUser,
    PartnerProfile,
    User,
    UserRole,
)
from app.auth.schemas import ClientRegister, ClientUserRegister, PartnerRegister, UserCreate
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.auth.utils import SecurityUtils
from app.config import settings
from app.core.mail import Mailer
from app.license.models import ClientLicense, PartnerLicense
from app.user.exceptions import (
    EmailAlreadyExistsException,
    UserClientNotFoundException,
    UsernameAlreadyExistsException,
    UserPartnerNotFoundException,
)
from app.user.utils import UserUtils


class AuthService:
    @staticmethod
    async def authenticate_user(session: AsyncSession, identifier: str, password: str) -> User:
        """
        Autentica o utilizador por e-mail ou username.
        identifier: Pode ser o e-mail ou o username do utilizador.
        """
        result = await session.execute(
            select(User).where(or_(User.email == identifier, User.username == identifier))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password):
            raise EmailUsernameOrPasswordException()
        if not user.is_active:
            raise InactiveUserException()

        if user.role in [UserRole.CLIENT_USER, UserRole.CLIENT]:
            await AuthService._verify_client_license(session, user.id)
        elif user.role == UserRole.PARTNER:
            await AuthService._verify_partner_license(session, user.id)

        return user

    @staticmethod
    async def _validate_uniqueness(session: AsyncSession, username: str, email: str) -> None:
        """
        Verificação se o username ou email já estão em uso.
        """
        query = select(User).where((User.username == username) | (User.email == email))
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.username == username:
                raise UsernameAlreadyExistsException()
            raise EmailAlreadyExistsException()

    @staticmethod
    async def _verify_client_license(session: AsyncSession, user_id: uuid.UUID):
        # Verifica se o user é o DONO (ClientProfile) ou FUNCIONÁRIO (ClientUser)
        # para encontrar o client_id correto

        # Primeiro tentamos ver se ele é funcionário
        stmt_user = select(ClientUser.client_id).where(ClientUser.user_id == user_id)
        res_user = await session.execute(stmt_user)
        client_id = res_user.scalar()

        # Se não for funcionário, verificamos se é o dono
        if not client_id:
            stmt_owner = select(ClientProfile.id).where(ClientProfile.user_id == user_id)
            res_owner = await session.execute(stmt_owner)
            client_id = res_owner.scalar()

        if not client_id:
            raise ProfileNotFoundException()

        stmt_lic = (
            select(ClientLicense)
            .where(ClientLicense.client_id == client_id)
            .where(ClientLicense.expiry_date >= datetime.now(timezone.utc))
            .where(ClientLicense.is_active)
        )
        res_lic = await session.execute(stmt_lic)
        if not res_lic.scalar_one_or_none():
            raise LicenseExpiredException()

    @staticmethod
    async def _verify_partner_license(session: AsyncSession, user_id: uuid.UUID):
        stmt = (
            select(PartnerLicense)
            .join(PartnerProfile, PartnerProfile.id == PartnerLicense.partner_id)
            .where(PartnerProfile.user_id == user_id)
            .where(PartnerLicense.expiry_date >= datetime.now(timezone.utc))
            .where(PartnerLicense.is_active)
        )
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            raise PartnerAccessExpiredException()

    @staticmethod
    async def create_admin(session: AsyncSession, user_in: UserCreate) -> User:
        """
        Cria um utilizador com privilégios de administrador.
        """
        await AuthService._validate_uniqueness(session, user_in.username, user_in.email)
        new_user = User(
            name=user_in.name,
            email=user_in.email,
            password=hash_password(user_in.password),
            username=user_in.username,
            role=UserRole.ADMIN,
        )
        session.add(new_user)

        try:
            await session.commit()
            await session.refresh(new_user)
            return new_user
        except Exception as e:
            await session.rollback()
            raise e

    @staticmethod
    async def register_partner(
        session: AsyncSession,
        data: PartnerRegister,
        background_tasks: BackgroundTasks,
    ) -> PartnerProfile:
        await AuthService._validate_uniqueness(session, data.user.username, data.user.email)
        otp_code = SecurityUtils.generate_otp_code()
        otp_expires = SecurityUtils.get_otp_expiration(minutes=30)

        new_user = User(
            name=data.user.name,
            email=data.user.email,
            username=data.user.username,
            password=hash_password(data.user.password),
            role=UserRole.PARTNER,
            is_active=False,
            is_verified=False,
            verification_code=otp_code,
            verification_code_expires=otp_expires,
        )

        session.add(new_user)
        await session.flush()

        new_profile = PartnerProfile(user_id=new_user.id, **data.profile.model_dump())
        session.add(new_profile)

        await session.commit()
        await session.refresh(new_profile)

        background_tasks.add_task(
            Mailer.send_email,
            subject='Verifique a sua conta - Teu ERP',
            recipients=[new_user.email],
            template_name='verify_email.html',
            body={
                'name': new_user.name,
                'code': otp_code,
                'expires_in': 30,
                'verify_url': f'{settings.FRONTEND_URL}/verify?email={new_user.email}',
            },
        )

        return new_profile

    @staticmethod
    async def register_client(session: AsyncSession, data: ClientRegister) -> ClientProfile:
        await AuthService._validate_uniqueness(session, data.user.username, data.user.email)
        new_user = User(
            name=data.user.name,
            email=data.user.email,
            username=data.user.username,
            password=hash_password(data.user.password),
            role=UserRole.CLIENT,
            is_verified=True,
        )
        session.add(new_user)
        await session.flush()

        partner_id = data.profile.partner_id
        result = await session.execute(
            select(PartnerProfile).where(PartnerProfile.id == partner_id)
        )
        partner = result.scalar_one_or_none()

        if not partner:
            raise UserPartnerNotFoundException()

        new_profile = ClientProfile(user_id=new_user.id, **data.profile.model_dump())
        session.add(new_profile)

        await session.commit()
        await session.refresh(new_profile)
        return new_profile

    @staticmethod
    async def register_client_user(session: AsyncSession, data: ClientUserRegister) -> ClientUser:
        await AuthService._validate_uniqueness(session, data.user.username, data.user.email)
        new_user = User(
            name=data.user.name,
            email=data.user.email,
            password=hash_password(data.user.password),
            username=data.user.username,
            role=UserRole.CLIENT_USER,
            is_verified=True,
        )
        session.add(new_user)
        await session.flush()

        client_id = data.employee_info.client_id
        result = await session.execute(select(ClientProfile).where(ClientProfile.id == client_id))
        client = result.scalar_one_or_none()

        if not client:
            raise UserClientNotFoundException()

        # Gera o código do funcionário
        data.employee_info.employee_id = UserUtils.generate_employee_code()
        data.employee_info.role_name = data.employee_info.role_name
        new_link = ClientUser(user_id=new_user.id, **data.employee_info.model_dump())
        session.add(new_link)

        await session.commit()
        await session.refresh(new_link)
        return new_link

    @staticmethod
    def create_tokens(user_id: uuid.UUID) -> Tuple[str, str]:
        access_token = create_access_token(subject=str(user_id))
        refresh_token = create_refresh_token(subject=str(user_id))
        return access_token, refresh_token
