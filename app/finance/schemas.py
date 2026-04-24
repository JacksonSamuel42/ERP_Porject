from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.finance.models import InvoiceStatus, LicenseTransactionType, PaymentStatus

# --- SCHEMAS PARA PAGAMENTO (PaymentLicense) ---


class PaymentLicenseBase(BaseModel):
    payment_method: Optional[str] = 'transfer'
    transaction_reference: Optional[str] = None


class PaymentLicenseCreate(PaymentLicenseBase):
    pass


class PaymentLicenseResponse(PaymentLicenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: LicenseTransactionType
    status: PaymentStatus
    amount: Decimal
    payment_date: Optional[datetime]
    created_at: datetime
    partner_license_id: Optional[UUID] = None
    client_license_id: Optional[UUID] = None


# --- SCHEMAS PARA FATURA (InvoiceLicense) ---


class InvoiceLicenseBase(BaseModel):
    base_amount: Decimal = Field(..., max_digits=10, decimal_places=2)
    tax_rate: float = 14.0
    due_date: datetime
    notes: Optional[str] = None


class InvoiceLicenseCreate(InvoiceLicenseBase):
    issuer_id: UUID  # ID do User que emite
    recipient_id: UUID  # ID do Profile (Client ou Partner)
    is_client: bool = True
    partner_license_id: Optional[UUID] = None
    client_license_id: Optional[UUID] = None


class InvoiceLicenseResponse(InvoiceLicenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_number: str
    tax_amount: Decimal
    total_amount: Decimal
    status: InvoiceStatus
    issue_date: datetime

    issuer_id: Optional[UUID]
    recipient_client_id: Optional[UUID]
    recipient_partner_id: Optional[UUID]
    partner_license_id: Optional[UUID]
    client_license_id: Optional[UUID]

    payments: List[PaymentLicenseResponse] = []

    can_be_cancelled: bool = True

    @classmethod
    def from_orm(cls, obj):
        instance = super().from_orm(obj)
        instance.can_be_cancelled = obj.status in [InvoiceStatus.DRAFT, InvoiceStatus.OPEN]
        return instance


# --- SCHEMAS DE UTILITÁRIOS / DASHBOARD ---


class PartnerRevenueResponse(BaseModel):
    partner_id: UUID
    total_revenue: Decimal
    count_invoices: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class FinanceSummary(BaseModel):
    pending_amount: Decimal
    paid_amount: Decimal
    total_invoices: int
