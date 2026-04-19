from fastapi import status

from app.exceptions import BaseException

# ---------- Plan Related Exceptions ----------


class PlanNotFoundException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='The specified ERP or Partner plan was not found',
        )


class PlanLimitExceededException(BaseException):
    def __init__(self, resource: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'Plan limit reached for: {resource}. Please upgrade your plan',
        )


# ---------- Partner Licensing Exceptions ----------


class PartnerNotAuthorizedException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Partner is not authorized to resell this specific ERP plan',
        )


class PartnerClientLimitReachedException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Partner has reached the maximum number of clients for their current plan',
        )


# ---------- Client Licensing & Machine Exceptions ----------
class LicenseNotFoundException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='License not found',
        )


class LicenseNotActiveException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='This license is currently disabled or suspended',
        )


class InvalidMachineHardwareException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Hardware signature mismatch. This machine is not authorized',
        )


class MachineActivationConflictException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail='This machine is already linked to another active license',
        )


class MaxMachinesReachedException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Maximum number of machines reached for this license',
        )


# ---------- Synchronization & Integrity ----------


class OfflineGracePeriodExpiredException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail='Maximum offline period reached. Please connect to the internet to verify license',
        )
