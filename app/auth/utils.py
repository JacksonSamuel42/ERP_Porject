import random
import secrets
import string
from datetime import datetime, timedelta, timezone


class SecurityUtils:
    @staticmethod
    def generate_otp_code(length: int = 6) -> str:
        """
        Gera um código numérico aleatório (ex: 849203).
        Ideal para verificação de e-mail rápida.
        """
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Gera um token aleatório longo para URLs (ex: reset de senha).
        Utiliza urlsafe para evitar caracteres problemáticos em links.
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def get_token_expiration(hours: int = 1) -> datetime:
        """Define o tempo de expiração para o token de reset."""
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    @staticmethod
    def get_otp_expiration(minutes: int = 30) -> datetime:
        """Define o tempo de expiração para o código OTP."""
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)

    @staticmethod
    def generate_random_password(
        length: int = 12,
        use_upper: bool = True,
        use_digits: bool = True,
        use_punctuation: bool = True,
    ) -> str:
        """
        Generate a secure random password using the `secrets` module.

        - length: total length of the password (minimum enforced to include required classes)
        - use_upper: include uppercase letters
        - use_digits: include digits
        - use_punctuation: include punctuation characters (some ambiguous characters excluded)
        """
        if length < 4:
            raise ValueError('password length must be at least 4')

        lower = string.ascii_lowercase
        upper = string.ascii_uppercase if use_upper else ''
        digits = string.digits if use_digits else ''
        # use a restricted set of punctuation to avoid problems with some systems
        punctuation = '!@#$%&*()-_=+[]' if use_punctuation else ''

        alphabet = lower + upper + digits + punctuation
        if not alphabet:
            raise ValueError('At least one character set must be enabled')

        # Ensure the password contains at least one character from each selected set
        password_chars = [secrets.choice(lower)]
        if use_upper:
            password_chars.append(secrets.choice(upper))
        if use_digits:
            password_chars.append(secrets.choice(digits))
        if use_punctuation:
            password_chars.append(secrets.choice(punctuation))

        # Fill the rest
        while len(password_chars) < length:
            password_chars.append(secrets.choice(alphabet))

        # Shuffle to avoid predictable sequences
        random.SystemRandom().shuffle(password_chars)

        return ''.join(password_chars)
