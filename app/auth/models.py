import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(enum.Enum):
    ADMIN = 'admin'
    PARTNER = 'partner'
    CLIENT = 'client'
    CLIENT_USER = 'client_user'


class ClientUserRole(enum.Enum):
    ADMIN_LOCAL = 'admin_local'
    GERENTE = 'gerente'
    CONTABILISTA = 'contabilista'
    TESOUREIRO = 'tesoureiro'
    FIEL_ARMAZEM = 'fiel_armazem'
    VENDEDOR = 'vendedor'
    CAIXA = 'caixa'
    GESTOR_RH = 'gestor_rh'


class User(Base):
    """Tabela central de autenticação e identidade"""

    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name='user_roles', values_callable=lambda x: [item.value for item in x]),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    pending_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    verification_code: Mapped[str] = mapped_column(String(10), nullable=True)
    verification_code_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reset_token: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    partner_profile: Mapped[Optional['PartnerProfile']] = relationship(
        'PartnerProfile', back_populates='user', uselist=False, lazy='raise'
    )
    client_profile: Mapped[Optional['ClientProfile']] = relationship(
        'ClientProfile', back_populates='user', uselist=False, lazy='raise'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if hasattr(self, 'role') and hasattr(self.role, 'value'):
            self.role = self.role.value


class PartnerProfile(Base):
    """Dados do Parceiro/Revendedor"""

    __tablename__ = 'partner_profiles'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    nif: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    logo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    street: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    building: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped['User'] = relationship('User', back_populates='partner_profile', lazy='raise')
    clients: Mapped[List['ClientProfile']] = relationship(
        'ClientProfile', back_populates='partner', lazy='raise'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()


class ClientProfile(Base):
    """Perfil da Empresa Cliente (Dono da Licença)"""

    __tablename__ = 'client_profiles'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('partner_profiles.id'), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nif: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    regime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    logo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    street: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    building: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped['User'] = relationship('User', back_populates='client_profile', lazy='raise')
    partner: Mapped['PartnerProfile'] = relationship(
        'PartnerProfile', back_populates='clients', lazy='raise'
    )
    users: Mapped[List['ClientUser']] = relationship(
        'ClientUser', back_populates='client', lazy='raise'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()


class ClientUser(Base):
    """Utilizadores operacionais dentro da empresa do cliente"""

    __tablename__ = 'client_users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('client_profiles.id'), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    role_name: Mapped[ClientUserRole] = mapped_column(
        SQLEnum(
            ClientUserRole,
            name='client_user_roles',
            values_callable=lambda x: [item.value for item in x],
        ),
        nullable=False,
    )
    permissions: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    employee_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_extension: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    server_version: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    client: Mapped['ClientProfile'] = relationship(
        'ClientProfile', back_populates='users', lazy='raise'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if self.permissions is None:
            self.permissions = {}
        if hasattr(self, 'role') and hasattr(self.role, 'value'):
            self.role = self.role.value


class AuditLog(Base):
    """Rastreabilidade de ações"""

    __tablename__ = 'audit_logs'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
