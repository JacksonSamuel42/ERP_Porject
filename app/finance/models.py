import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentStatus(enum.Enum):
    PENDING = 'pendente'
    PAID = 'pago'
    CANCELLED = 'cancelado'
    REFUNDED = 'reembolsado'


class LicenseTransactionType(enum.Enum):
    PARTNER_SUBSCRIPTION = 'partner_subscription'
    CLIENT_LICENSE = 'client_license'


class InvoiceStatus(enum.Enum):
    DRAFT = 'rascunho'
    OPEN = 'aberto'
    PAID = 'pago'
    CANCELLED = 'cancelado'
    OVERDUE = 'vencido'


class InvoiceLicense(Base):
    """
    Faturas exclusivas para licenciamento de software.
    """

    __tablename__ = 'invoice_licenses'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    base_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # Valor sem imposto
    tax_amount: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.00
    )  # Valor do imposto (ex: IVA)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # Base + Tax

    tax_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), default=14.00
    )  # Percentual aplicado (ex: 14.00 para 14%)

    issuer_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('users.id'), nullable=True)
    recipient_client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('client_profiles.id'), nullable=True
    )
    recipient_partner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('partner_profiles.id'), nullable=True
    )

    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus, values_callable=lambda x: [item.value for item in x]),
        default=InvoiceStatus.DRAFT,
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    payments: Mapped[List['PaymentLicense']] = relationship(
        'PaymentLicense', back_populates='invoice'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()


class PaymentLicense(Base):
    """
    Registros de pagamentos específicos para licenças.
    """

    __tablename__ = 'payment_licenses'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type: Mapped[LicenseTransactionType] = mapped_column(
        SQLEnum(LicenseTransactionType, values_callable=lambda x: [item.value for item in x]),
        nullable=False,
    )

    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('invoice_licenses.id'), nullable=True
    )

    partner_license_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('partner_licenses.id'), nullable=True
    )
    client_license_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('client_licenses.id'), nullable=True
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, values_callable=lambda x: [item.value for item in x]),
        default=PaymentStatus.PENDING,
    )

    payment_method: Mapped[Optional[str]] = mapped_column(String)  # 'transfer', 'cash', 'gateway'
    transaction_reference: Mapped[str] = mapped_column(String)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    invoice: Mapped['InvoiceLicense'] = relationship('InvoiceLicense', back_populates='payments')

    __table_args__ = (
        CheckConstraint(
            '(partner_license_id IS NOT NULL AND client_license_id IS NULL) OR '
            '(partner_license_id IS NULL AND client_license_id IS NOT NULL)',
            name='check_payment_license_source',
        ),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
