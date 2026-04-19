import base64
import json
import random
import string
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.license.models import LicensePeriod


class LicenseCrypto:
    @staticmethod
    def generate_key_pair():
        """Gera um par de chaves RSA de 2048 bits."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Exportar Privada (Fica no Servidor/Secrets)
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Exportar Pública (Vai embutida no PySide6/Rust)
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return priv_pem, pub_pem

    @staticmethod
    def sign_license_data(data: dict, private_key_pem: bytes) -> str:
        """Assina o dicionário de dados e retorna o bundle em Base64."""
        # Ordenar chaves para garantir que o JSON seja sempre idêntico
        payload = json.dumps(data, sort_keys=True).encode('utf-8')

        private_key = serialization.load_pem_private_key(private_key_pem, password=None)

        signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())

        bundle = {'data': data, 'signature': base64.b64encode(signature).decode('utf-8')}

        # Retorna o bundle final como string para salvar no campo license_key
        return json.dumps(bundle)


def calculate_expiration(start_date: datetime, period: LicensePeriod) -> datetime:
    """Calcula a data de expiração baseada no período da licença."""
    if period == LicensePeriod.MENSAL:
        return start_date + timedelta(days=30)
    elif period == LicensePeriod.TRIMESTRAL:
        return start_date + timedelta(days=90)
    elif period == LicensePeriod.SEMESTRAL:
        return start_date + timedelta(days=180)
    elif period == LicensePeriod.ANUAL:
        return start_date + timedelta(days=365)
    return start_date + timedelta(days=30)


def generate_partner_key(prefix: str = 'PRT') -> str:
    """Gera uma chave aleatória simples: PRT-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    return f'{prefix}-{datetime.now().year}-' + '-'.join(parts)
