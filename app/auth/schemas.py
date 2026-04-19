import re
import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing_extensions import Doc

from app.auth.models import ClientUserRole

# ---------- Users ----------


class LoginRequest(BaseModel):
    identifier: EmailStr | str
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            'example': {'identifier': 'user@example.com', 'password': 'securepassword123'}
        }
    )


class UserBase(BaseModel):
    name: Annotated[str, Doc('Nome completo do utilizador')]
    email: Annotated[EmailStr, Doc('Email único para autenticação')]
    username: Annotated[Optional[str], Doc('Nome de utilizador único')]
    role: Optional[str] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, value: Optional[str]):
        if not value:
            return value

        value = value.lower().strip()
        if len(value) < 3 or len(value) > 20:
            raise ValueError('Username must be between 3 and 20 characters.')

        if not re.match(r'^[a-z0-9_]+$', value):
            raise ValueError('Username can only contain letters, numbers, and underscores.')

        if value[0].isdigit():
            raise ValueError('Username cannot start with a number.')

        return value


class UserCreate(UserBase):
    password: Annotated[str, Doc('Senha em plain text')]

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Valida se a senha tem:
        - Pelo menos 8 caracteres
        - Pelo menos uma letra maiúscula
        - Pelo menos um número
        - Pelo menos um caractere especial
        """
        if len(v) < 8:
            raise ValueError('A senha deve ter pelo menos 8 caracteres.')

        if not re.search(r'[A-Z]', v):
            raise ValueError('A senha deve conter pelo menos uma letra maiúscula.')

        if not re.search(r'[0-9]', v):
            raise ValueError('A senha deve conter pelo menos um número.')

        if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', v):
            raise ValueError('A senha deve conter pelo menos um caractere especial.')

        return v

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'username': 'johndoe',
                'password': 'securepassword123',
            }
        }
    )


class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(use_enum_values=True)


# ---------- Profile Schemas ----------


class PartnerProfileBase(BaseModel):
    company_name: str
    nif: str
    email: EmailStr
    province: Optional[str] = None
    municipality: Optional[str] = None
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    building: Optional[str] = None

    @field_validator('nif')
    @classmethod
    def validate_nif_angola(cls, v: str):
        if v is None:
            return v
        # Padrão simplificado: 10 dígitos (empresas) ou 10 dígitos + letra (singular)
        pattern = r'^\d{10}([a-zA-Z]{1})?$'
        if not re.match(pattern, v):
            raise ValueError(
                'NIF inválido para o padrão de Angola. Deve conter 10 dígitos e opcionalmente uma letra.'
            )
        return v.upper()

    model_config = ConfigDict(from_attributes=True)


class PartnerProfileResponse(PartnerProfileBase):
    id: uuid.UUID
    logo: Optional[str] = None
    user_id: uuid.UUID


class ClientProfileBase(BaseModel):
    partner_id: uuid.UUID
    name: str
    legal_name: Optional[str] = None
    nif: str
    email: EmailStr
    phone_number: Optional[str] = None
    website: Optional[str] = None
    regime: Optional[str] = None
    registration_number: Optional[str] = None
    province: Optional[str] = None
    municipality: Optional[str] = None
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    building: Optional[str] = None

    @field_validator('nif')
    @classmethod
    def validate_nif_angola(cls, v: str):
        if v is None:
            return v
        # Padrão simplificado: 10 dígitos (empresas) ou 10 dígitos + letra (singular)
        pattern = r'^\d{10}([a-zA-Z]{1})?$'
        if not re.match(pattern, v):
            raise ValueError(
                'NIF inválido para o padrão de Angola. Deve conter 10 dígitos e opcionalmente uma letra.'
            )
        return v.upper()

    # model_config = ConfigDict(
    #     json_schema_extra={
    #         "example": {
    #             "name": "",
    #             "legal_name": "",
    #             "nif": "",
    #             "email": "",
    #             "phone_number": "",
    #             "website": "",
    #             "regime": "",
    #             "registration_number": "",
    #             "province": "",
    #             "municipality": "",
    #             "street": "",
    #             "neighborhood": "",
    #             "building": ""
    #         }
    #     }
    # )


class ClientProfileResponse(ClientProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    logo: Optional[str] = None
    updated_at: datetime


class ClientUserBase(BaseModel):
    client_id: uuid.UUID
    role_name: ClientUserRole
    permissions: Dict[str, Any] = Field(default_factory=dict)
    employee_id: Optional[str] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    phone_extension: Optional[str] = None


class ClientUserResponse(ClientUserBase):
    id: uuid.UUID
    user_id: uuid.UUID
    server_version: int
    is_deleted: bool

    model_config = ConfigDict(use_enum_values=True)


# ---------- Composite Schemas ----------


class PartnerRegister(BaseModel):
    user: UserCreate
    profile: PartnerProfileBase


class ClientRegister(BaseModel):
    user: UserCreate
    profile: ClientProfileBase


class ClientUserRegister(BaseModel):
    user: UserCreate
    employee_info: ClientUserBase


# ---------- AuditLog ----------


class AuditLogBase(BaseModel):
    actor_id: uuid.UUID
    action_type: str
    target_id: Optional[uuid.UUID] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    id: uuid.UUID
    created_at: datetime
