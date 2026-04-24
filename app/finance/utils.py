import random
import string
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal


class InvoiceUtils:
    @staticmethod
    def generate_invoice_number(prefix: str = 'INV-LIC') -> str:
        """
        Gera um código de fatura único no formato: PREFIX-YYYY-XXXXX
        Exemplo: INV-LIC-2026-A8B3C
        """
        year = datetime.now(timezone.utc).year
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        return f'{prefix}-{year}-{random_suffix}'

    @staticmethod
    def calculate_invoice_totals(base_amount: float, tax_rate_percent: float = 14.00) -> dict:
        """
        Calcula o imposto e o total usando Decimal para precisão financeira.
        Retorna um dicionário com base, imposto e total.
        """
        base = Decimal(str(base_amount))
        rate = Decimal(str(tax_rate_percent)) / Decimal('100')

        tax = (base * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = base + tax

        return {
            'base_amount': float(base),
            'tax_amount': float(tax),
            'total_amount': float(total),
            'tax_rate': float(tax_rate_percent),
        }
