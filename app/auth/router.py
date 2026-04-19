import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import CurrentSession, RoleChecker, UserRole, validate_token
from app.auth.exceptions import InvalidCredentialsException
from app.auth.schemas import (
    ClientProfileResponse,
    ClientRegister,
    ClientUserRegister,
    ClientUserResponse,
    LoginRequest,
    PartnerProfileResponse,
    PartnerRegister,
    UserCreate,
    UserResponse,
)
from app.auth.service import AuthService

router = APIRouter(prefix='/auth', tags=['Authentication'])

# --- LOGIN ---


@router.post('/login/docs', summary='Login específico para Swagger UI')
async def login_swagger(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: CurrentSession,
):
    user = await AuthService.authenticate_user(
        session=session, identifier=form_data.username, password=form_data.password
    )
    access_token, refresh_token = AuthService.create_tokens(user.id)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
    }


@router.post('/login', summary='Official login for the app')
async def login(
    login_data: LoginRequest,
    session: CurrentSession,
):
    user = await AuthService.authenticate_user(
        session=session, identifier=login_data.identifier, password=login_data.password
    )
    access_token, refresh_token = AuthService.create_tokens(user.id)

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        # 'user': UserResponse(
        #     id=user.id,
        #     name=user.name,
        #     email=user.email,
        #     username=user.username,
        #     role=user.role,
        #     is_active=user.is_active,
        #     is_verified=user.is_verified,
        #     created_at=user.created_at,
        # ),
    }


@router.post('/refresh')
async def refresh_token(token_payload: Annotated[dict, Depends(validate_token)]):
    if token_payload.get('type') != 'refresh':
        raise InvalidCredentialsException()

    user_id = uuid.UUID(token_payload.get('sub'))
    new_access_token = AuthService.create_tokens(user_id)[0]

    return {'access_token': new_access_token, 'token_type': 'bearer'}


# REGISTRATION
@router.post(
    '/register/admin',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
)
async def register_admin(user_in: UserCreate, session: CurrentSession):
    """
    Endpoint para criar utilizadores com nível de acesso administrativo.
    """
    return await AuthService.create_admin(session, user_in)


@router.post(
    '/register/partner',
    response_model=PartnerProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
)
async def register_partner(
    payload: PartnerRegister, session: CurrentSession, background_tasks: BackgroundTasks
):
    """
    Cria um Utilizador com role PARTNER e o seu respectivo PartnerProfile.
    """
    return await AuthService.register_partner(session, payload, background_tasks)


@router.post(
    '/register/client',
    response_model=ClientProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.PARTNER]))],
)
async def register_client(payload: ClientRegister, session: CurrentSession):
    """
    Cria um Utilizador com role CLIENT e o seu respectivo ClientProfile (Empresa).
    """
    return await AuthService.register_client(session, payload)


@router.post(
    '/register/client-user',
    response_model=ClientUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN, UserRole.PARTNER, UserRole.CLIENT]))],
)
async def register_client_user(
    payload: ClientUserRegister,
    session: CurrentSession,
):
    """
    Cria um utilizador operacional vinculado a uma empresa (ClientProfile).
    """
    return await AuthService.register_client_user(session, payload)
