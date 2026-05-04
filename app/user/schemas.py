import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password(cls, v: str) -> str:
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


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return validate_password(cls, v)

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdatePassword(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return validate_password(cls, v)

    model_config = ConfigDict(from_attributes=True)


class EmailUpdateRequest(BaseModel):
    new_email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class ResendConfirmationRequest(BaseModel):
    email: EmailStr


class PartnerProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    nif: Optional[str] = None
    email: Optional[EmailStr] = None  # Email comercial
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


class ClientProfileUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None
    regime: Optional[str] = None
    logo: Optional[str] = None
    province: Optional[str] = None
    municipality: Optional[str] = None
    street: Optional[str] = None
    neighborhood: Optional[str] = None
    building: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClientUserUpdate(BaseModel):
    department: Optional[str] = None
    phone_extension: Optional[str] = None
    role_name: Optional[str] = None
    permissions: Optional[dict] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
