from app.exceptions import BaseException, status


class InvoiceNotFoundException(BaseException):
    def __init__(self):
        super().__init__('Invoice not found', status.HTTP_404_NOT_FOUND)


class PaymentRequiredException(BaseException):
    def __init__(self):
        super().__init__('Payment pending for this license', status.HTTP_402_PAYMENT_REQUIRED)


class DuplicateInvoiceException(BaseException):
    def __init__(self):
        super().__init__('Invoice already exists with this number', status.HTTP_409_CONFLICT)


class InvalidPaymentAmountException(BaseException):
    def __init__(self):
        super().__init__('Payment amount does not match invoice total', status.HTTP_400_BAD_REQUEST)


class TaxCalculationException(BaseException):
    def __init__(self):
        super().__init__(
            'Erro ao calcular impostos da fatura', status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class InvoiceExpiredException(BaseException):
    def __init__(self):
        super().__init__('Invoice expired', status.HTTP_410_GONE)


class InvalidInvoiceStateException(BaseException):
    def __init__(self, current_status: str):
        super().__init__(f'Invalid invoice state: {current_status}', status.HTTP_400_BAD_REQUEST)


class IllegalStatusTransitionException(BaseException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            f'Not possible transition from {from_status} to {to_status}',
            status.HTTP_400_BAD_REQUEST,
        )


class PaymentRefundException(BaseException):
    def __init__(self, detail: str):
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)


class PaymentNotFoundException(BaseException):
    def __init__(self):
        super().__init__('Payment not found', status.HTTP_404_NOT_FOUND)
