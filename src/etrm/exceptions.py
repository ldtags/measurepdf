class ETRMConnectionError(BaseException):
    def __init__(self, message: str | None=None):
        self.message = message or 'An eTRM connection layer error occurred'
        super().__init__()


class ETRMRequestError(ETRMConnectionError):
    def __init__(self, message: str | None=None):
        super().__init__(message or 'Request to the eTRM database failed')


class ETRMResponseError(ETRMConnectionError):
    def __init__(self, message: str | None=None, status: int=500):
        self.status = status
        super().__init__(message or 'Server error')


class UnauthorizedError(ETRMRequestError):
    def __init__(self, message: str | None=None):
        self.message = message or 'Unauthorized request'
        super().__init__(self.message)
