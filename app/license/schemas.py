import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Doc

from app.license.models import LicensePeriod

# ---------- PartnerLicense ----------


class PartnerLicenseAssign(BaseModel):
    """Schema para o Admin atribuir um plano de revenda a um Parceiro."""

    partner_id: UUID = Field(..., description='ID do Parceiro que receberá o plano')
    partner_plan_id: UUID = Field(..., description='ID do PartnerPlan (regras de revenda)')
    period: LicensePeriod = Field(..., description='Período: MENSAL, TRIMESTRAL, SEMESTRAL, ANUAL')

    class Config:
        from_attributes = True


class PartnerLicenseBase(BaseModel):
    partner_id: Annotated[uuid.UUID, Doc('ID of the partner profile')]
    partner_plan_id: Annotated[uuid.UUID, Doc('ID of the assigned PartnerPlan')]
    expiry_date: Annotated[datetime, Doc('License expiration timestamp')]
    period: Annotated[LicensePeriod, Doc('Billing cycle: mensal, anual, etc.')]


class PartnerLicenseCreate(PartnerLicenseBase):
    pass


class PartnerLicenseUpdate(BaseModel):
    expiry_date: Optional[datetime] = None
    period: Optional[LicensePeriod] = None
    is_active: Optional[bool] = None


class PartnerLicenseResponse(PartnerLicenseBase):
    id: uuid.UUID
    start_date: datetime
    license_key: Optional[str]
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        populate_by_name=True,
    )


# ---------- ClientLicense ----------


class ClientLicenseEmit(BaseModel):
    """Schema para o Parceiro emitir uma licença para um Cliente final."""

    client_id: UUID = Field(..., description='ID do Cliente que vai usar o ERP')
    erp_plan_id: UUID = Field(..., description='ID do ERPPlan (funcionalidades do software)')
    period: LicensePeriod = Field(..., description='Duração da licença')
    offline_only: Optional[bool] = Field(None, description='Se a licença é para uso offline apenas')


class ClientLicenseBase(BaseModel):
    client_id: Annotated[uuid.UUID, Doc('ID of the client company')]
    partner_id: Annotated[uuid.UUID, Doc('ID of the partner who issued the license')]
    erp_plan_id: Annotated[uuid.UUID, Doc('ID of the ERPPlan')]
    expiry_date: Annotated[datetime, Doc('License expiration timestamp')]
    period: Annotated[LicensePeriod, Doc('Billing cycle')]
    offline_only: Annotated[bool, Doc('Whether the license is for offline use only')]
    license_metadata: Annotated[
        Dict[str, Any], Doc('Configuration data for the offline desktop client')
    ] = Field(default_factory=dict)


class ClientLicenseCreate(ClientLicenseBase):
    pass


class ClientLicenseUpdate(BaseModel):
    expiry_date: Optional[datetime] = None
    period: Optional[LicensePeriod] = None
    authorized_machines: Optional[List[str]] = None
    license_metadata: Optional[Dict[str, Any]] = None
    offline_only: Optional[bool] = None


class ClientLicenseResponse(ClientLicenseBase):
    id: uuid.UUID
    start_date: datetime
    license_key: Optional[str]

    authorized_machines: Annotated[
        List[str], Doc('List of activated hardware IDs (e.g., Motherboard UUIDs)')
    ]

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )
