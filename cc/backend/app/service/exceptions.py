from __future__ import annotations


class ServiceException(Exception):
    error_code: str | None = None

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class ValidationException(ServiceException):
    error_code = "VALIDATION_ERROR"


class NotFoundException(ServiceException):
    error_code = "NOT_FOUND"


class ConflictException(ServiceException):
    error_code = "CONFLICT"


class RepositoryException(ServiceException):
    error_code = "REPOSITORY_ERROR"
