import uuid
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Doc


class PartnerPlanBase(BaseModel):
    name: Annotated[str, Doc('Commercial name of the partner level (e.g., Gold, Silver)')]
    max_clients: Annotated[
        Optional[int],
        Doc('Maximum number of clients this partner can manage. Null means unlimited'),
    ] = None
    allowed_erp_plans: Annotated[
        List,
        Doc('List of ERP Plan IDs that this partner is authorized to resell'),
    ] = Field(default_factory=list)


class PartnerPlanCreate(PartnerPlanBase):
    pass


class PartnerPlanUpdate(BaseModel):
    name: Optional[str] = None
    max_clients: Optional[int] = None
    allowed_erp_plans: Optional[List] = None


class PartnerPlanResponse(PartnerPlanBase):
    id: uuid.UUID

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'id': '770e8400-e29b-41d4-a716-446655440001',
                'name': 'Premium Reseller',
                'max_clients': 50,
                'allowed_erp_plans': ['550e8400-e29b-41d4-a716-446655440002'],
            }
        },
    )


# ---------- ERPPlan ----------


class ERPPlanBase(BaseModel):
    name: Annotated[str, Doc('Name of the ERP feature package')]
    default_max_machines: Annotated[
        Optional[int], Doc('Default hardware activation limit. Null means unlimited')
    ] = 1
    modules_enabled: Annotated[
        Dict[str, bool],
        Doc("Mapping of active modules (e.g., {'billing': true, 'hr': false})"),
    ]
    sync_enabled: Annotated[
        bool,
        Doc('Whether sync is enabled for this plan'),
    ] = True
    plan_ranges: Annotated[
        Dict[str, Any], Doc('Quantitative limits such as max users or document quotas')
    ] = Field(default_factory=dict)


class ERPPlanCreate(ERPPlanBase):
    pass


class ERPPlanUpdate(BaseModel):
    name: Optional[str] = None
    default_max_machines: Optional[int] = None
    modules_enabled: Optional[Dict[str, bool]] = None
    sync_enabled: Optional[bool] = None
    plan_ranges: Optional[Dict[str, Any]] = None


class ERPPlanResponse(ERPPlanBase):
    id: uuid.UUID

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'example': {
                'id': '550e8400-e29b-41d4-a716-446655440002',
                'name': 'Standard Business',
                'default_max_machines': 3,
                'sync_enabled': True,
                'modules_enabled': {'billing': True, 'inventory': True, 'pos': True},
                'plan_ranges': {'max_users': 5, 'max_monthly_invoices': 1000},
            }
        },
    )
