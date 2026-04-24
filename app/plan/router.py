import uuid

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.auth.dependencies import CurrentSession, allow_admin, allow_any, allow_partner
from app.plan.schemas import (
    ERPPlanCreate,
    ERPPlanResponse,
    ERPPlanUpdate,
    PartnerPlanCreate,
    PartnerPlanResponse,
    PartnerPlanUpdate,
)
from app.plan.service import PlanService

router = APIRouter(prefix='/plans', tags=['Plans Management'])

# --- ERP PLANS ENDPOINTS ---


@router.post(
    '/erp',
    response_model=ERPPlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(allow_admin)],
)
async def create_erp_plan(payload: ERPPlanCreate, session: CurrentSession):
    """Cria um novo plano de funcionalidades para o ERP."""
    return await PlanService.create_erp_plan(session=session, **payload.model_dump())


@router.get('/erp', response_model=Page[ERPPlanResponse], dependencies=[Depends(allow_any)])
async def list_erp_plans(session: CurrentSession, is_active: bool = True):
    """Lista todos os planos ERP disponíveis para novas licenças."""
    return await PlanService.list_erp_plans(session, is_active)


@router.get('/erp/{plan_id}', response_model=ERPPlanResponse, dependencies=[Depends(allow_any)])
async def get_erp_plan(plan_id: uuid.UUID, session: CurrentSession):
    """Busca um plano ERP específico."""
    return await PlanService.get_erp_plan_by_id(session, plan_id)


@router.patch(
    '/erp/{plan_id}',
    response_model=ERPPlanResponse,
    dependencies=[Depends(allow_admin)],
)
async def update_erp_plan(plan_id: uuid.UUID, payload: ERPPlanUpdate, session: CurrentSession):
    """Atualiza um plano ERP existente."""
    return await PlanService.update_erp_plan(
        session, plan_id, **payload.model_dump(exclude_unset=True)
    )


@router.delete(
    '/erp/{plan_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(allow_admin)],
)
async def delete_erp_plan(plan_id: uuid.UUID, session: CurrentSession):
    """Deleta um plano ERP existente."""
    await PlanService.delete_erp_plan(session, plan_id)
    return {'message': 'ERP plan deleted successfully'}


# --- PARTNER PLANS ENDPOINTS ---


@router.post(
    '/partner',
    response_model=PartnerPlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(allow_admin)],
)
async def create_partner_plan(payload: PartnerPlanCreate, session: CurrentSession):
    """Cria um novo plano de parceiro."""
    return await PlanService.create_partner_plan(session=session, **payload.model_dump())


@router.get(
    '/partner', response_model=Page[PartnerPlanResponse], dependencies=[Depends(allow_partner)]
)
async def list_partner_plans(session: CurrentSession, is_active: bool = True):
    """Lista todos os planos de parceiro disponíveis para novos contratos."""
    return await PlanService.list_partner_plans(session, is_active)


@router.get(
    '/partner/{plan_id}', response_model=PartnerPlanResponse, dependencies=[Depends(allow_any)]
)
async def get_partner_plan(plan_id: uuid.UUID, session: CurrentSession):
    """Busca um plano de parceiro específico."""
    return await PlanService.get_partner_plan_by_id(session, plan_id)


@router.patch(
    '/partner/{plan_id}',
    response_model=PartnerPlanResponse,
    dependencies=[Depends(allow_admin)],
)
async def update_partner_plan(
    plan_id: uuid.UUID, payload: PartnerPlanUpdate, session: CurrentSession
):
    """Atualiza um plano de parceiro existente."""
    return await PlanService.update_partner_plan(
        session, plan_id, **payload.model_dump(exclude_unset=True)
    )


@router.delete(
    '/partner/{plan_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(allow_admin)],
)
async def delete_partner_plan(plan_id: uuid.UUID, session: CurrentSession):
    """Deleta um plano de parceiro existente."""
    await PlanService.delete_partner_plan(session, plan_id)
    return {'message': 'Partner plan deleted successfully'}
