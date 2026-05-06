import uuid
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Path, status

from app.auth.dependencies import CurrentSession, CurrentUser, RoleChecker, allow_any
from app.auth.models import UserRole
from app.license.schemas import (
    LICENSE_REGEX,
    ClientLicenseEmit,
    ClientLicenseResponse,
    LicenseVerifyResponse,
    PartnerLicenseAssign,
    PartnerLicenseResponse,
)
from app.license.service import LicenseService

router = APIRouter(prefix='/licenses', tags=['Licensing'])


@router.post(
    '/assign-to-partner',
    response_model=PartnerLicenseResponse,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
)
async def assign_license_to_partner(
    data: PartnerLicenseAssign, session: CurrentSession, current_user: CurrentUser
):
    """O Admin atribui/vende um plano de revenda a um Parceiro."""
    return await LicenseService.assign_license_to_partner(
        session,
        user_id=current_user.id,
        partner_id=data.partner_id,
        partner_plan_id=data.partner_plan_id,
        period=data.period,
    )


@router.post(
    '/emit-client',
    response_model=ClientLicenseResponse,
    dependencies=[Depends(RoleChecker([UserRole.PARTNER]))],
)
async def emit_client_license(
    data: ClientLicenseEmit,
    current_user: CurrentUser,
    session: CurrentSession,
):
    """
    O Parceiro emite uma licença para o seu cliente.
    """

    return await LicenseService.emit_client_license(
        session,
        user_id=current_user.id,
        client_id=data.client_id,
        erp_plan_id=data.erp_plan_id,
        period=data.period,
        offline_only=data.offline_only,
        expiry_date=None,  # O service já calcula via utils
    )


@router.patch('/clients/{client_id}/upgrade-offline')
async def upgrade_to_offline(
    client_id: uuid.UUID,
    session: CurrentSession,
    current_user: CurrentUser,
):
    return await LicenseService.upgrade_client_offline_mode(session, client_id, current_user.id)


@router.get(
    '/my-license',
    response_model=Union[ClientLicenseResponse, PartnerLicenseResponse],
    dependencies=[Depends(RoleChecker([UserRole.CLIENT, UserRole.CLIENT_USER, UserRole.PARTNER]))],
)
async def get_my_license(
    current_user: CurrentUser,
    session: CurrentSession,
):
    if current_user.role == UserRole.PARTNER:
        return await LicenseService.get_partner_license(session, current_user)
    return await LicenseService.get_client_license(session, current_user)


@router.get(
    '/client/verify/{client_id}',
    response_model=LicenseVerifyResponse,
    dependencies=[Depends(allow_any)],
)
async def verify_client_license(
    client_id: uuid.UUID,
    session: CurrentSession,
    current_user: CurrentUser,
):
    """Verifica se a licença do cliente é válida."""
    res = await LicenseService.is_license_valid(session, client_id)
    return {'valid': res}


@router.get(
    '/partner/verify/{license_key}',
    response_model=LicenseVerifyResponse,
    dependencies=[Depends(allow_any)],
)
async def verify_license(
    license_key: Annotated[
        str,
        Path(pattern=LICENSE_REGEX, title='Chave da Licença', examples=['PRT-2026-GVO3-AQK6-TYTF']),
    ],
    session: CurrentSession,
    current_user: CurrentUser,
):
    """Verifica se a licença do parceiro é válida."""
    res = await LicenseService.verify_partner_license(session, license_key)
    return {'valid': res}


@router.post(
    '/activate/{machine_id}', response_model=ClientLicenseResponse, status_code=status.HTTP_200_OK
)
async def activate_license(
    machine_id: str,
    current_user: CurrentUser,
    session: CurrentSession,
):
    """
    Endpoint chamado pelo App Desktop para vincular o Hardware ID à licença.
    Retorna a license_key (RSA) atualizada com todos os módulos e o novo ID.
    """
    client_id = await LicenseService.get_client_id_from_user(session, current_user.id)
    return await LicenseService.activate_client_machine(
        session=session, client_id=client_id, machine_id=machine_id
    )
