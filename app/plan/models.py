import uuid
from typing import Dict, Optional

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PartnerPlan(Base):
    """Planos que definem o nível e o poder de revenda do Parceiro"""

    __tablename__ = 'partner_plans'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    max_clients: Mapped[Optional[int]] = mapped_column(Integer)

    # Lista de IDs de ERPPlans que este parceiro tem permissão para revender
    # Ex: ["uuid_plano_basico", "uuid_plano_pro"]
    allowed_erp_plans: Mapped[dict] = mapped_column(JSON, default={})
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)

    def __init__(
        self, name: str, max_clients: int = None, allowed_erp_plans: Optional[Dict] = None
    ) -> None:
        """Convenience constructor for PartnerPlan."""
        self.name = name
        self.max_clients = max_clients
        self.allowed_erp_plans = allowed_erp_plans if allowed_erp_plans is not None else {}

    def is_at_limit(self, current_count: int) -> bool:
        if self.max_clients is None:
            return False
        return current_count >= self.max_clients


class ERPPlan(Base):
    """
    Planos de Funcionalidades ERP com limites (ranges).
    """

    __tablename__ = 'erp_plans'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)  # 'Pequeno Negócio', 'Corporativo'
    default_max_machines: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Módulos ativos: {"billing": true, "inventory": true, "hr": false}
    modules_enabled: Mapped[dict] = mapped_column(JSON)

    # Ranges/Limites: {"users": [1, 5], "items": [0, 1000]} ou apenas {"users_limit": 5}
    plan_ranges: Mapped[dict] = mapped_column(JSON, default={})

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __init__(
        self,
        name: str,
        is_active: bool = True,
        modules_enabled: Optional[Dict] = None,
        plan_ranges: Optional[Dict] = None,
        default_max_machines: Optional[int] = None,
        sync_enabled: bool = True,
    ) -> None:
        """Convenience constructor for ERPPlan."""
        self.name = name
        self.is_active = is_active
        self.modules_enabled = modules_enabled if modules_enabled is not None else {}
        self.plan_ranges = plan_ranges if plan_ranges is not None else {}
        self.sync_enabled = sync_enabled
        self.default_max_machines = default_max_machines
