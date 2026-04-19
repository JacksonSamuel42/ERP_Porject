from app.exceptions import BaseException, status

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


class ERPPlanNotFoundException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail='ERP plan not found or inactive.'
        )


class PartnerPlanNotFoundException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Partner plan not found or inactive.',
        )


class PlanAlreadyInactiveException(BaseException):
    def __init__(self):
        super().__init__(detail='This plan is already inactive.')


class InvalidPlanDataException(BaseException):
    def __init__(self, message: str = 'Invalid plan data.'):
        super().__init__(detail=message)
