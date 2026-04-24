import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks, UploadFile
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import ProfileNotFoundException
from app.auth.models import AuditLog, ClientProfile, ClientUser, PartnerProfile, User
from app.auth.security import hash_password, verify_password
from app.auth.utils import SecurityUtils
from app.config import settings
from app.core.mail import Mailer
from app.core.upload_utils import S3UploadUtils
from app.user.exceptions import (
    CodeExpiredException,
    CurrentPasswordException,
    InvalidCodeException,
    InvalidTokenException,
    UserAlreadyActiveException,
    UserAlreadyInactiveException,
    UserCannotDeactivateException,
    UserEmailAlreadyInUseException,
    UserNotFoundException,
)
from app.user.schemas import (
    ClientProfileUpdate,
    ClientUserUpdate,
    EmailUpdateRequest,
    PartnerProfileUpdate,
    UserUpdate,
    UserUpdatePassword,
)


class UserService:
    @staticmethod
    async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundException()
        return user

    @staticmethod
    async def get_partner(session: AsyncSession, partner_id: uuid.UUID) -> PartnerProfile:
        partner = await session.get(PartnerProfile, partner_id)
        if not partner:
            raise ProfileNotFoundException()
        return partner

    @staticmethod
    async def get_client(session: AsyncSession, client_id: uuid.UUID) -> ClientProfile:
        client = await session.get(ClientProfile, client_id)
        if not client:
            raise ProfileNotFoundException()
        return client

    @staticmethod
    async def get_client_user(session: AsyncSession, client_user_id: uuid.UUID) -> ClientUser:
        client_user = await session.get(ClientUser, client_user_id)
        if not client_user:
            raise ProfileNotFoundException()
        return client_user

    # --- MÉTODOS DE LISTAGEM PAGINADA COM FILTROS ---

    @staticmethod
    async def get_all_users(session: AsyncSession, filters: Optional[dict] = None):
        """Lista todos os usuários com filtros de busca e status."""
        query = select(User).order_by(User.name)

        if filters:
            if filters.get('is_active') is not None:
                query = query.where(User.is_active == filters['is_active'])
            if filters.get('is_verified') is not None:
                query = query.where(User.is_verified == filters['is_verified'])
            if filters.get('search'):
                s = f'%{filters["search"]}%'
                query = query.where(or_(User.name.ilike(s), User.email.ilike(s)))

        return await paginate(session, query)

    @staticmethod
    async def get_all_partners(session: AsyncSession, filters: Optional[dict] = None):
        """Lista perfis de parceiros com filtros comerciais."""
        query = select(PartnerProfile).order_by(PartnerProfile.company_name)

        if filters:
            if filters.get('search'):
                s = f'%{filters["search"]}%'
                query = query.where(
                    or_(PartnerProfile.company_name.ilike(s), PartnerProfile.cnpj.ilike(s))
                )

        return await paginate(session, query)

    @staticmethod
    async def get_all_clients(
        session: AsyncSession,
        partner_id: Optional[uuid.UUID] = None,
        filters: Optional[dict] = None,
    ):
        """Lista clientes, opcionalmente filtrados por um parceiro específico."""
        query = select(ClientProfile).order_by(ClientProfile.name)

        if partner_id:
            query = query.where(ClientProfile.partner_id == partner_id)

        if filters:
            if filters.get('search'):
                s = f'%{filters["search"]}%'
                query = query.where(or_(ClientProfile.name.ilike(s), ClientProfile.email.ilike(s)))

        return await paginate(session, query)

    @staticmethod
    async def get_all_client_users(
        session: AsyncSession, client_id: uuid.UUID, filters: Optional[dict] = None
    ):
        """Lista usuários/funcionários de um cliente específico."""
        query = select(ClientUser).where(ClientUser.client_id == client_id).order_by(ClientUser.id)

        if filters and filters.get('role_name'):
            query = query.where(ClientUser.role_name == filters['role_name'])

        return await paginate(session, query)

    # -------------------------------------------------------
    #
    @staticmethod
    async def verify_email(session: AsyncSession, email: str, code: str):
        """Valida o OTP e ativa a conta do usuário."""
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or user.verification_code != code:
            raise InvalidCodeException()

        if datetime.now(timezone.utc) > user.verification_code_expires:
            raise CodeExpiredException()

        user.is_verified = True
        user.is_active = True
        user.verification_code = None
        user.verification_code_expires = None

        await session.commit()
        return {'message': 'Account successfully verified.'}

    @staticmethod
    async def resend_confirmation(
        session: AsyncSession, email: str, background_tasks: BackgroundTasks
    ):
        """
        Reenvia o código de verificação para o e-mail fornecido.
        """
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or user.is_verified:
            return {'message': 'If the account is not verified, a new code has been sent.'}

        otp_code = SecurityUtils.generate_otp_code()
        user.verification_code = otp_code
        user.verification_code_expires = SecurityUtils.get_otp_expiration(minutes=15)

        await session.commit()

        background_tasks.add_task(
            Mailer.send_email,
            subject='Verify your account - Project G',
            recipients=[user.email],
            template_name='verify_email.html',
            body={'name': user.name, 'code': otp_code, 'expires_in': 15},
        )
        return {'message': 'A new verification code has been sent to your email.'}

    @staticmethod
    async def request_password_reset(
        session: AsyncSession, email: str, background_tasks: BackgroundTasks
    ):
        """Gera token de recuperação e envia e-mail."""
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            token = SecurityUtils.generate_secure_token()
            user.reset_token = token
            user.reset_token_expires = SecurityUtils.get_token_expiration(hours=1)
            await session.commit()

            background_tasks.add_task(
                Mailer.send_email,
                subject='Recuperação de Senha - Teu ERP',
                recipients=[user.email],
                template_name='reset_password.html',
                body={
                    'name': user.name,
                    'reset_url': f'{settings.FRONTEND_URL}/reset-password?token={token}',
                },
            )

        return {'message': 'If the email address exists, the instructions have been sent.'}

    @staticmethod
    async def reset_password(session: AsyncSession, token: str, new_password: str):
        """Valida o token e atualiza a senha."""
        result = await session.execute(select(User).where(User.reset_token == token))
        user = result.scalar_one_or_none()

        if not user or datetime.now(timezone.utc) > user.reset_token_expires:
            raise InvalidTokenException()

        user.password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None

        await session.commit()
        return {'message': 'Password updated successfully.'}

    @staticmethod
    async def update_password(session: AsyncSession, user_id: uuid.UUID, data: UserUpdatePassword):
        """Troca de senha para usuário logado."""
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException()

        if not verify_password(data.current_password, user.password):
            raise CurrentPasswordException()

        user.password = hash_password(data.new_password)
        await session.commit()
        return {'message': 'Password changed successfully.'}

    @staticmethod
    async def request_email_update(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: EmailUpdateRequest,
        background_tasks: BackgroundTasks,
    ):
        """
        Inicia o processo de troca de e-mail.
        Gera um OTP e envia para o NOVO e-mail pretendido.
        """
        existing_user = await session.execute(select(User).where(User.email == data.new_email))
        if existing_user.scalar_one_or_none():
            raise UserEmailAlreadyInUseException()

        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundException()

        otp_code = SecurityUtils.generate_otp_code()
        user.verification_code = otp_code
        user.verification_code_expires = SecurityUtils.get_otp_expiration(minutes=15)
        user.pending_email = data.new_email

        await session.commit()

        background_tasks.add_task(
            Mailer.send_email,
            subject='Confirm your new email address',
            recipients=[data.new_email],
            template_name='request_email_change.html',
            body={
                'name': user.name,
                'code': otp_code,
                'expires_in': 15,
                'verify_url': f'{settings.FRONTEND_URL}/confirm-email?email={data.new_email}',
            },
        )
        return {'message': 'Verification code sent to the new email address.'}

    @staticmethod
    async def confirm_email_update(session: AsyncSession, user_id: uuid.UUID, code: str):
        """
        Valida o código e finalmente altera o e-mail no banco de dados.
        """
        user = await session.get(User, user_id)
        if not user:
            raise UserNotFoundException()

        if user.verification_code != code:
            raise InvalidCodeException()

        if datetime.now(timezone.utc) > user.verification_code_expires:
            raise CodeExpiredException()

        old_email = user.email
        new_email = user.pending_email

        user.email = new_email
        user.pending_email = None
        user.verification_code = None
        user.verification_code_expires = None

        audit = AuditLog(
            actor_id=user_id,
            action_type='EMAIL_UPDATE',
            target_id=user_id,
            details={'old_email': old_email, 'new_email': new_email},
        )
        session.add(audit)

        await session.commit()
        return {'message': 'Email updated successfully.'}

    @staticmethod
    async def update_profile(session: AsyncSession, user_id: str, data: UserUpdate):
        """Atualiza dados básicos do perfil."""
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException()

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        await session.commit()
        return user

    @staticmethod
    async def update_partner_profile(
        session: AsyncSession, user_id: uuid.UUID, data: PartnerProfileUpdate
    ):
        """Atualiza os dados comerciais do Parceiro."""
        result = await session.execute(
            select(PartnerProfile).where(PartnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise ProfileNotFoundException()

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        await session.commit()
        await session.refresh(profile)

        if profile.logo:
            profile.logo_url = await S3UploadUtils.generate_presigned_url(profile.logo)

        return profile

    @staticmethod
    async def update_client_profile(
        session: AsyncSession, user_id: uuid.UUID, data: ClientProfileUpdate
    ):
        """Atualiza os dados da empresa Cliente."""
        result = await session.execute(
            select(ClientProfile).where(ClientProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise ProfileNotFoundException()

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        await session.commit()
        await session.refresh(profile)

        if profile.logo:
            profile.logo_url = await S3UploadUtils.generate_presigned_url(profile.logo)

        return profile

    @staticmethod
    async def update_client_user_info(
        session: AsyncSession, user_id: uuid.UUID, data: ClientUserUpdate
    ):
        """Atualiza dados operacionais de um funcionário do cliente."""
        result = await session.execute(select(ClientUser).where(ClientUser.user_id == user_id))
        client_user = result.scalar_one_or_none()

        if not client_user:
            raise ProfileNotFoundException()

        update_data = data.model_dump(exclude_unset=True)

        if 'permissions' in update_data and client_user.permissions:
            current_perms = dict(client_user.permissions)
            current_perms.update(update_data['permissions'])
            client_user.permissions = current_perms
            del update_data['permissions']

        for key, value in update_data.items():
            setattr(client_user, key, value)

        await session.commit()
        await session.refresh(client_user)
        return client_user

    @staticmethod
    async def deactivate_user(session: AsyncSession, user_id: uuid.UUID, actor_id: uuid.UUID):
        """
        Desativa um utilizador (Soft Delete).
        actor_id: ID de quem está a realizar a ação (para auditoria).
        """
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException()

        if not user.is_active:
            raise UserAlreadyInactiveException()

        if user_id == actor_id:
            raise UserCannotDeactivateException()

        user.is_active = False

        audit = AuditLog(
            actor_id=actor_id,
            action_type='USER_DEACTIVATION',
            target_id=user_id,
            details={'reason': 'Administrative request', 'user_email': user.email},
        )
        session.add(audit)

        await session.commit()
        return {'status': 'success', 'message': f'User {user.email} deactivated successfully.'}

    @staticmethod
    async def activate_user(session: AsyncSession, user_id: uuid.UUID, actor_id: uuid.UUID):
        """Reativa um utilizador anteriormente desativado."""
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException()
        elif user.is_active:
            raise UserAlreadyActiveException()

        user.is_active = True

        audit = AuditLog(
            actor_id=actor_id,
            action_type='USER_ACTIVATION',
            target_id=user_id,
            details={'user_email': user.email},
        )
        session.add(audit)

        await session.commit()
        return {'status': 'success', 'message': 'User activated successfully.'}

    @staticmethod
    async def update_partner_logo(session: AsyncSession, user_id: uuid.UUID, file: UploadFile):
        """Atualiza a logo do parceiro e remove a anterior."""
        result = await session.execute(
            select(PartnerProfile).where(PartnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise ProfileNotFoundException()

        # Salvar novo ficheiro
        new_logo_path = await S3UploadUtils.save_file(file, folder='partner_logos')

        # Apagar logo antiga se existir
        if profile.logo:
            S3UploadUtils.delete_file(profile.logo)

        # Atualizar DB
        profile.logo = new_logo_path
        await session.commit()

        return {'logo_url': new_logo_path}

    @staticmethod
    async def upload_client_logo(session: AsyncSession, user_id: uuid.UUID, file: UploadFile):
        """Atualiza a logo do cliente e remove a anterior."""
        result = await session.execute(
            select(ClientProfile).where(ClientProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            raise ProfileNotFoundException()

        # Salvar novo ficheiro
        new_logo_path = await S3UploadUtils.save_file(file, folder='client_logos')

        # Apagar logo antiga se existir
        if profile.logo:
            S3UploadUtils.delete_file(profile.logo)

        # Atualizar DB
        profile.logo = new_logo_path
        await session.commit()

        return {'logo_url': new_logo_path}
