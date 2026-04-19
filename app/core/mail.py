from typing import Any, Dict, List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
    TEMPLATE_FOLDER=str(settings.TEMPLATE_FOLDER),
)


class Mailer:
    @staticmethod
    async def send_email(
        subject: str, recipients: List[EmailStr], body: Dict[str, Any], template_name: str
    ):
        """
        Envia e-mail usando templates HTML.
        """
        message = MessageSchema(
            subject=subject, recipients=recipients, template_body=body, subtype=MessageType.html
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name=template_name)

    @staticmethod
    async def send_simple_text(subject: str, recipients: List[EmailStr], content: str):
        """
        Envia um e-mail de texto simples (útil para logs ou alertas rápidos).
        """
        message = MessageSchema(
            subject=subject, recipients=recipients, body=content, subtype=MessageType.plain
        )
        fm = FastMail(conf)
        await fm.send_message(message)
