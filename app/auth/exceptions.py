from fastapi import status

from app.exceptions import BaseException


class InvalidCredentialsException(BaseException):
    def __init__(self):
        super().__init__(detail='Could not validate credentials')


class InactiveUserException(BaseException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail='User account is inactive')


class PasswordMismatchException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='New password and confirmation do not match',
        )


class WeakPasswordException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Password is too weak. should contain at least 8 characters, including uppercase, lowercase, numbers, and special characters',
        )


class UsernameAlreadyExistsException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username already exists',
        )


class EmailUsernameOrPasswordException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='The provided email/username or password is incorrect',
        )


class IncorrectPasswordException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='The current password provided is incorrect',
        )


# License Exception


class LicenseExpiredException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail='Client license has expired. Please contact your partner',
        )


class PartnerAccessExpiredException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail='Partner subscription is inactive. Access to management panel denied',
        )


class MachineLimitReachedException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Maximum number of authorized machines reached for this license',
        )


class UnauthorizedMachineException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='This machine is not authorized to use this license',
        )


class ProfileNotFoundException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Profile not found',
        )


class PartnerNotAuthorizedException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Partner is not authorized to access this resource',
        )


# RBAC
class PermissionDeniedException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You do not have the required permissions to perform this action',
        )
