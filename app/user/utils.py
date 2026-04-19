import random
import string
from datetime import datetime


class UserUtils:
    @staticmethod
    def generate_employee_code(length: int = 4) -> str:
        """
        Gera um código no formato EMP-ANO-RANDOM (ex: EMP-2026-K9P2)
        """
        year = datetime.now().year
        # Gera uma sequência aleatória de letras maiúsculas e números
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

        return f'EMP-{year}-{random_str}'
