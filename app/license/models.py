import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LicensePeriod(enum.Enum):
    MENSAL = 'mensal'
    TRIMESTRAL = 'trimestral'
    SEMESTRAL = 'semestral'
    ANUAL = 'anual'


class PartnerLicense(Base):
    """Subscrição do Parceiro para acesso ao painel de revenda"""

    __tablename__ = 'partner_licenses'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('partner_profiles.id'))
    partner_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('partner_plans.id'))

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    period: Mapped[LicensePeriod] = mapped_column(
        SQLEnum(
            LicensePeriod,
            name='partner_license_periods',
            values_callable=lambda x: [item.value for item in x],
        ),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    license_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __init__(
        self,
        partner_id: uuid.UUID,
        partner_plan_id: uuid.UUID,
        expiry_date: datetime,
        period: LicensePeriod,
        start_date: Optional[datetime] = None,
        is_active: bool = True,
        license_key: Optional[str] = None,
    ) -> None:
        """Convenience constructor for PartnerLicense."""
        if not isinstance(period, LicensePeriod):
            raise TypeError('period must be a LicensePeriod enum member')
        self.partner_id = partner_id
        self.partner_plan_id = partner_plan_id
        self.start_date = start_date or datetime.utcnow()
        self.expiry_date = expiry_date
        self.period = period
        self.is_active = is_active
        self.license_key = license_key


class ClientLicense(Base):
    """Licença emitida para o software final instalado no cliente"""

    __tablename__ = 'client_licenses'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('client_profiles.id'))
    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('partner_profiles.id'))
    erp_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('erp_plans.id'))

    offline_only: Mapped[bool] = mapped_column(Boolean, default=False)
    authorized_machines: Mapped[dict] = mapped_column(JSON, default=[])
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    period: Mapped[LicensePeriod] = mapped_column(
        SQLEnum(
            LicensePeriod,
            name='client_license_periods',
            values_callable=lambda x: [item.value for item in x],
        ),
        nullable=False,
    )

    # Metadata para o Offline-First (Configurações que o Desktop lerá)
    # Ex: {"last_sync": "...", "enforce_limits": true}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    license_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license_metadata: Mapped[dict] = mapped_column(JSON, default={})

    def __init__(
        self,
        client_id: uuid.UUID,
        partner_id: uuid.UUID,
        erp_plan_id: uuid.UUID,
        expiry_date: datetime,
        period: LicensePeriod,
        is_active: bool = True,
        authorized_machines: Optional[str] = None,
        start_date: Optional[datetime] = None,
        license_key: Optional[str] = None,
        offline_only: bool = False,
        license_metadata: Optional[Dict] = None,
    ) -> None:
        """Convenience constructor for ClientLicense."""

        if not isinstance(period, LicensePeriod):
            raise TypeError('period must be a LicensePeriod enum member')
        self.client_id = client_id
        self.partner_id = partner_id
        self.erp_plan_id = erp_plan_id
        self.is_active = is_active
        self.authorized_machines = authorized_machines
        self.start_date = start_date or datetime.utcnow()
        self.expiry_date = expiry_date
        self.period = period
        self.license_key = license_key
        self.offline_only = offline_only
        self.license_metadata = license_metadata if license_metadata is not None else {}
