import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.plan.exceptions import (
    ERPPlanNotFoundException,
    PartnerPlanNotFoundException,
    PlanAlreadyInactiveException,
)
from app.plan.models import ERPPlan, PartnerPlan


class PlanService:
    @staticmethod
    async def create_erp_plan(
        session: AsyncSession,
        name: str,
        modules_enabled: Dict,
        plan_ranges: Dict,
        default_max_machines: Optional[int] = 1,
        sync_enabled: bool = True,
    ) -> ERPPlan:
        """Cria um novo plano de funcionalidades para o ERP."""
        new_plan = ERPPlan(
            name=name,
            modules_enabled=modules_enabled,
            plan_ranges=plan_ranges,
            default_max_machines=default_max_machines,
            sync_enabled=sync_enabled,
            is_active=True,
        )
        session.add(new_plan)
        await session.commit()
        await session.refresh(new_plan)
        return new_plan

    @staticmethod
    async def get_erp_plan_by_id(session: AsyncSession, plan_id: uuid.UUID) -> ERPPlan:
        """Busca um plano ERP específico."""
        result = await session.execute(select(ERPPlan).where(ERPPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise ERPPlanNotFoundException()
        return plan

    @staticmethod
    async def update_erp_plan(
        session: AsyncSession, plan_id: uuid.UUID, **update_data
    ) -> Optional[ERPPlan]:
        """Atualiza dados de um plano ERP ativo."""
        plan = await PlanService.get_erp_plan_by_id(session, plan_id)

        if not plan:
            raise ERPPlanNotFoundException()
        if not plan.is_active:
            raise PlanAlreadyInactiveException()

        if 'plan_ranges' in update_data and update_data['plan_ranges']:
            new_ranges = update_data.pop('plan_ranges')
            current_ranges = dict(plan.plan_ranges or {})
            current_ranges.update(new_ranges)
            plan.plan_ranges = current_ranges

        if 'modules_enabled' in update_data and update_data['modules_enabled']:
            new_modules = update_data.pop('modules_enabled')
            current_modules = dict(plan.modules_enabled or {})
            current_modules.update(new_modules)
            plan.modules_enabled = current_modules

        for key, value in update_data.items():
            if hasattr(plan, key) and value is not None:
                setattr(plan, key, value)

        await session.commit()
        await session.refresh(plan)
        return plan

    @staticmethod
    async def delete_erp_plan(session: AsyncSession, plan_id: uuid.UUID) -> bool:
        """Marca plano ERP como inativo (Soft Delete)."""
        plan = await PlanService.get_erp_plan_by_id(session, plan_id)
        if not plan or not plan.is_active:
            raise ERPPlanNotFoundException()

        plan.is_active = False
        await session.commit()
        return True

    # --- PARTNER PLANS (Planos de Revenda) ---

    @staticmethod
    async def create_partner_plan(
        session: AsyncSession, name: str, max_clients: int, allowed_erp_plans: List[str]
    ) -> PartnerPlan:
        """Cria um plano que define o que o parceiro pode revender."""
        new_plan = PartnerPlan(
            name=name, max_clients=max_clients, allowed_erp_plans=allowed_erp_plans
        )
        session.add(new_plan)
        await session.commit()
        await session.refresh(new_plan)
        return new_plan

    @staticmethod
    async def get_partner_plan_by_id(session: AsyncSession, plan_id: uuid.UUID) -> PartnerPlan:
        """Busca um plano de parceiro específico."""
        result = await session.execute(select(PartnerPlan).where(PartnerPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise PartnerPlanNotFoundException()
        return plan

    @staticmethod
    async def update_partner_plan(
        session: AsyncSession, plan_id: uuid.UUID, **update_data
    ) -> Optional[PartnerPlan]:
        """Atualiza plano de parceiro ativo."""
        plan = await PlanService.get_partner_plan_by_id(session, plan_id)

        if not plan:
            raise ERPPlanNotFoundException()
        if not plan.is_active:
            raise PlanAlreadyInactiveException()

        if 'allowed_erp_plans' in update_data:
            new_plans = update_data.pop('allowed_erp_plans')
            current_list = list(plan.allowed_erp_plans or [])
            for p_id in new_plans:
                if p_id not in current_list:
                    current_list.append(p_id)

            plan.allowed_erp_plans = current_list
            flag_modified(plan, 'allowed_erp_plans')

        for key, value in update_data.items():
            if hasattr(plan, key) and value is not None:
                setattr(plan, key, value)

        await session.commit()
        await session.refresh(plan)
        return plan

    @staticmethod
    async def delete_partner_plan(session: AsyncSession, plan_id: uuid.UUID) -> bool:
        """Marca plano de parceiro como inativo."""
        plan = await PlanService.get_partner_plan_by_id(session, plan_id)

        if not plan or not plan.is_active:
            raise PartnerPlanNotFoundException()

        plan.is_active = False
        await session.commit()
        return True

    # --- LISTAGENS ---

    @staticmethod
    async def list_erp_plans(session: AsyncSession) -> List[ERPPlan]:
        """Lista todos os planos ERP disponíveis para novas licenças."""
        result = await session.execute(
            select(ERPPlan).where(ERPPlan.is_active).order_by(ERPPlan.name)
        )
        return result.scalars().all()

    @staticmethod
    async def list_partner_plans(session: AsyncSession) -> List[PartnerPlan]:
        """Lista todos os planos de parceiro disponíveis para novos contratos."""
        result = await session.execute(
            select(PartnerPlan).where(PartnerPlan.is_active).order_by(PartnerPlan.name)
        )
        return result.scalars().all()
