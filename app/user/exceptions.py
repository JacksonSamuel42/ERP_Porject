from app.exceptions import BaseException, status


class UserNotFoundException(BaseException):
    def __init__(self):
        super().__init__('User not found.', status.HTTP_404_NOT_FOUND)


class UsernameAlreadyExistsException(BaseException):
    def __init__(self):
        super().__init__('Username already exists.', status.HTTP_400_BAD_REQUEST)


class EmailAlreadyExistsException(BaseException):
    def __init__(self):
        super().__init__('Email already exists.', status.HTTP_400_BAD_REQUEST)


class InvalidCodeException(BaseException):
    def __init__(self):
        super().__init__('Invalid verification code.')


class CodeExpiredException(BaseException):
    def __init__(self, detail: str = 'Verification code has expired. Please request a new one.'):
        super().__init__(detail)


class InvalidTokenException(BaseException):
    def __init__(self):
        super().__init__('Invalid or expired recovery token.', status.HTTP_401_UNAUTHORIZED)


class UserAlreadyInactiveException(BaseException):
    def __init__(self):
        super().__init__('This user is already inactive.', status.HTTP_400_BAD_REQUEST)


class UserAlreadyActiveException(BaseException):
    def __init__(self):
        super().__init__('This user is already active.', status.HTTP_400_BAD_REQUEST)


class UserCannotDeactivateException(BaseException):
    def __init__(self):
        super().__init__('Cannot deactivate this user account.', status.HTTP_403_FORBIDDEN)


class UserEmailAlreadyInUseException(BaseException):
    def __init__(self):
        super().__init__('This email is already in use.', status.HTTP_400_BAD_REQUEST)


class UserPartnerNotFoundException(BaseException):
    def __init__(self):
        super().__init__('Partner not found.', status.HTTP_404_NOT_FOUND)


class UserClientNotFoundException(BaseException):
    def __init__(self):
        super().__init__('Client not found.', status.HTTP_404_NOT_FOUND)


class CurrentPasswordException(BaseException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Current password is incorrect',
        )
