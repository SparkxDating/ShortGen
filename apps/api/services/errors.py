class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, message: str = "not found") -> None:
        super().__init__(message, status_code=404)


class UnauthorizedError(ServiceError):
    def __init__(self, message: str = "unauthorized") -> None:
        super().__init__(message, status_code=401)


class ForbiddenError(ServiceError):
    def __init__(self, message: str = "forbidden") -> None:
        super().__init__(message, status_code=403)


class ConflictError(ServiceError):
    def __init__(self, message: str = "conflict") -> None:
        super().__init__(message, status_code=409)
