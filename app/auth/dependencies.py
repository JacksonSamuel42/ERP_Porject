import uuid
from datetime import datetime, timezone
from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config import auth_settings
from app.auth.constants import HEADER_MACHINE_ID
from app.auth.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
    LicenseExpiredException,
    PartnerAccessExpiredException,
    PartnerNotAuthorizedException,
    PermissionDeniedException,
    UnauthorizedMachineException,
)
from app.auth.models import ClientProfile, ClientUser, PartnerProfile, User, UserRole
from app.database import AsyncSessionLocal
from app.license.models import ClientLicense, PartnerLicense
from app.user.exceptions import UserClientNotFoundException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login/docs')


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def validate_token(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """Decodes and validates the JWT token."""
    try:
        payload = jwt.decode(token, auth_settings.JWT_SECRET, algorithms=[auth_settings.JWT_ALG])
        user_id: str = payload.get('sub')
        if user_id is None:
            raise InvalidCredentialsException()
        return payload
    except JWTError:
        raise InvalidCredentialsException()


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    token_payload: Annotated[dict, Depends(validate_token)],
    x_machine_id: Annotated[Optional[str], Header(alias=HEADER_MACHINE_ID)] = None,
) -> User:
    """
    Main dependency to get the current authenticated user.
    Validates user status, client licenses (with hardware binding),
    and partner subscriptions.
    """
    user_id = token_payload.get('sub')

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise InactiveUserException()

    if user.role in [UserRole.CLIENT_USER, UserRole.CLIENT]:
        if user.role == UserRole.CLIENT:
            client_stmt = select(ClientProfile.id).where(ClientProfile.user_id == user.id)
        else:
            client_stmt = select(ClientUser.client_id).where(ClientUser.user_id == user.id)
        client_res = await session.execute(client_stmt)
        target_client_id = client_res.scalar_one_or_none()

        if not target_client_id:
            raise UserClientNotFoundException()

        stmt = (
            select(ClientLicense)
            .where(ClientLicense.client_id == target_client_id)
            .where(ClientLicense.is_active)
            .where(ClientLicense.expiry_date >= datetime.now(timezone.utc))
        )
        license_res = await session.execute(stmt)
        active_license = license_res.scalar_one_or_none()

        if not active_license:
            raise LicenseExpiredException()

        # Hardware ID Binding Check
        if active_license.authorized_machines:
            if not x_machine_id or x_machine_id not in active_license.authorized_machines:
                raise UnauthorizedMachineException()

    elif user.role == UserRole.PARTNER:
        stmt = (
            select(PartnerLicense)
            .join(PartnerProfile, PartnerProfile.id == PartnerLicense.partner_id)
            .where(PartnerProfile.user_id == user.id)
            .where(PartnerLicense.is_active)
            .where(PartnerLicense.expiry_date >= datetime.now(timezone.utc))
        )
        partner_lic_res = await session.execute(stmt)
        if not partner_lic_res.scalar_one_or_none():
            raise PartnerAccessExpiredException()

    return user


async def get_active_partner_license(
    partner_id: uuid.UUID, session: Annotated[AsyncSession, Depends(get_session)]
) -> PartnerLicense:
    stmt = select(PartnerLicense).where(
        PartnerLicense.partner_id == partner_id,
        PartnerLicense.is_active,
        PartnerLicense.expiry_date >= datetime.now(timezone.utc),
    )
    result = await session.execute(stmt)
    license = result.scalar_one_or_none()

    if not license:
        raise PartnerNotAuthorizedException()

    return license


class RoleChecker:
    """
    Dependency to restrict access based on User Roles.
    Usage: Depends(RoleChecker([UserRole.ADMIN, UserRole.PARTNER]))
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles:
            raise PermissionDeniedException()
        return user


CurrentSession = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

allow_admin = RoleChecker([UserRole.ADMIN])
allow_partner = RoleChecker([UserRole.PARTNER, UserRole.ADMIN])
allow_client = RoleChecker([UserRole.CLIENT, UserRole.CLIENT_USER, UserRole.ADMIN])
allow_any = RoleChecker([UserRole.ADMIN, UserRole.PARTNER, UserRole.CLIENT, UserRole.CLIENT_USER])
