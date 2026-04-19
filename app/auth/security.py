from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext

from app.auth.config import auth_settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a JWT Access Token.
    The 'sub' (subject) field contains the User ID.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + auth_settings.JWT_EXP

    to_encode = {'exp': expire, 'sub': str(subject), 'type': 'access'}

    encoded_jwt = jwt.encode(to_encode, auth_settings.JWT_SECRET, algorithm=auth_settings.JWT_ALG)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + auth_settings.REFRESH_TOKEN_EXP

    to_encode = {'exp': expire, 'sub': str(subject), 'type': 'refresh'}

    encoded_jwt = jwt.encode(
        to_encode,
        auth_settings.REFRESH_TOKEN_KEY,
        algorithm=auth_settings.JWT_ALG,
    )
    return encoded_jwt
