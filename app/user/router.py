import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi_pagination import Page

from app.auth.dependencies import (
    CurrentSession,
    CurrentUser,
    RoleChecker,
    allow_admin,
    allow_client,
    allow_partner,
)
from app.auth.models import ClientUserRole, UserRole
from app.auth.schemas import (
    ClientProfileResponse,
    ClientUserResponse,
    PartnerProfileResponse,
    UserResponse,
)
from app.core.upload_utils import S3UploadUtils
from app.user.schemas import (
    ClientProfileUpdate,
    ClientUserUpdate,
    EmailUpdateRequest,
    ForgotPasswordRequest,
    PartnerProfileUpdate,
    ResendConfirmationRequest,
    ResetPasswordRequest,
    UserUpdate,
    UserUpdatePassword,
    VerifyEmailRequest,
)
from app.user.service import UserService

router = APIRouter(prefix='/users', tags=['Users'])


@router.get('/', response_model=Page[UserResponse])
async def list_users(
    session: CurrentSession,
    current_user: CurrentUser,
    search: Optional[str] = None,
    active: Optional[bool] = None,
    verified: Optional[bool] = None,
):
    filters = {'search': search, 'is_active': active, 'is_verified': verified}
    return await UserService.get_all_users(session, filters=filters)


@router.get('/me', response_model=Any)
async def get_my_profile(
    current_user: CurrentUser,
    session: CurrentSession,
):
    return {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'username': current_user.username,
        'role': current_user.role,
        'is_active': current_user.is_active,
        'is_verified': current_user.is_verified,
        'created_at': current_user.created_at,
    }


@router.get('/{user_id}', response_model=UserResponse)
async def get_user(user_id: uuid.UUID, session: CurrentSession, current_user: CurrentUser):
    return await UserService.get_user(session, user_id)


# PROFILE
@router.get('/partners/all', response_model=Page[PartnerProfileResponse])
async def list_partners(
    session: CurrentSession,
    current_user: CurrentUser,
    search: Optional[str] = None,
):
    filters = {'search': search}
    page = await UserService.get_all_partners(session, filters=filters)

    for partner in page.items:
        if partner.logo:
            partner.logo = await S3UploadUtils.generate_presigned_url(partner.logo)
    return page


@router.get('/partners/{partner_id}', response_model=PartnerProfileResponse)
async def get_partner(partner_id: uuid.UUID, session: CurrentSession, current_user: CurrentUser):
    return await UserService.get_partner(session, partner_id)


@router.get('/clients/all', response_model=Page[ClientProfileResponse])
async def list_clients(
    session: CurrentSession,
    current_user: CurrentUser,
    partner_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
):
    """Admin ou Parceiro listando clientes."""
    filters = {'search': search}

    page = await UserService.get_all_clients(session, partner_id=partner_id, filters=filters)

    for client in page.items:
        if client.logo:
            client.logo = await S3UploadUtils.generate_presigned_url(client.logo)
    return page


@router.get('/clients/{client_id}', response_model=ClientProfileResponse)
async def get_client(client_id: uuid.UUID, session: CurrentSession, current_user: CurrentUser):
    return await UserService.get_client(session, client_id)


@router.get('/clients/{client_id}/users', response_model=Page[ClientUserResponse])
async def list_client_users(
    session: CurrentSession,
    current_user: CurrentUser,
    client_id: uuid.UUID,
    role_name: Optional[ClientUserRole] = None,
):
    filters = {'role_name': role_name}
    return await UserService.get_all_client_users(session, client_id=client_id, filters=filters)


@router.get('/client-users/{client_user_id}', response_model=ClientUserResponse)
async def get_client_user(
    client_user_id: uuid.UUID, session: CurrentSession, current_user: CurrentUser
):
    return await UserService.get_client_user(session, client_user_id)


@router.post('/verify-email', status_code=status.HTTP_200_OK)
async def verify_email(data: VerifyEmailRequest, session: CurrentSession):
    return await UserService.verify_email(session, data.email, data.code)


@router.post('/resend-confirmation', status_code=status.HTTP_200_OK)
async def resend_confirmation(
    data: ResendConfirmationRequest,
    background_tasks: BackgroundTasks,
    session: CurrentSession,
):
    """
    Endpoint público para solicitar novo código de ativação.
    """
    return await UserService.resend_confirmation(session, data.email, background_tasks)


@router.post('/password-reset/request')
async def request_password_reset(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: CurrentSession,
):
    return await UserService.request_password_reset(session, data.email, background_tasks)


@router.post('/password-reset/reset')
async def reset_password(
    data: ResetPasswordRequest,
    session: CurrentSession,
):
    return await UserService.reset_password(session, data.token, data.new_password)


@router.patch('/me', response_model=Any)
async def update_my_basic_info(
    data: UserUpdate,
    current_user: CurrentUser,
    session: CurrentSession,
):
    user = await UserService.update_profile(session, str(current_user.id), data)
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'username': user.username,
        'role': user.role,
        'is_active': user.is_active,
        'is_verified': user.is_verified,
        'created_at': user.created_at,
    }


@router.post('/me/logo', dependencies=[Depends(RoleChecker([UserRole.PARTNER, UserRole.CLIENT]))])
async def upload_my_logo(
    current_user: CurrentUser,
    session: CurrentSession,
    file: UploadFile = File(...),
):
    if current_user.role == UserRole.PARTNER:
        return await UserService.update_partner_logo(session, current_user.id, file)
    elif current_user.role == UserRole.CLIENT:
        return await UserService.upload_client_logo(session, current_user.id, file)


@router.put('/me/password')
async def update_my_password(
    data: UserUpdatePassword,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.update_password(session, current_user.id, data)


@router.post('/me/email-update/request')
async def request_my_email_update(
    data: EmailUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.request_email_update(session, current_user.id, data, background_tasks)


@router.post('/me/email-update/confirm')
async def confirm_my_email_update(
    code: str,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.confirm_email_update(session, current_user.id, code)


@router.patch('/me/profile/partner', dependencies=[Depends(allow_partner)])
async def update_partner_details(
    data: PartnerProfileUpdate,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.update_partner_profile(session, current_user.id, data)


@router.patch('/me/profile/client', dependencies=[Depends(allow_client)])
async def update_client_details(
    data: ClientProfileUpdate,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.update_client_profile(session, current_user.id, data)


@router.patch('/me/profile/client-user', dependencies=[Depends(allow_client)])
async def update_client_employee_details(
    data: ClientUserUpdate,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.update_client_user_info(session, current_user.id, data)


# ADMINISTRATIVE


@router.delete('/{user_id}/deactivate', dependencies=[Depends(allow_admin)])
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.deactivate_user(session, user_id, current_user.id)


@router.post('/{user_id}/activate', dependencies=[Depends(allow_admin)])
async def activate_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    session: CurrentSession,
):
    return await UserService.activate_user(session, user_id, current_user.id)
