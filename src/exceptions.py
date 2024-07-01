"""Error classes for package-specific exceptions."""

class ETRMConnectionError(BaseException):
    def __init__(self, message: str | None=None):
        self.message = message or 'An error occurred within the eTRM connection layer'
        super().__init__()


class ETRMRequestError(ETRMConnectionError):
    def __init__(self, message: str | None=None):
        self.message = message or 'Request to the eTRM database failed'
        super().__init__(self.message)


class ETRMResponseError(ETRMConnectionError):
    def __init__(self, message: str | None=None):
        self.message = message or 'Invalid response from the eTRM'
        super().__init__(self.message)


class UnauthorizedError(ETRMRequestError):
    def __init__(self, message: str | None=None):
        self.message = message or 'Unauthorized request'
        super().__init__(self.message)


class NotFoundError(ETRMRequestError):
    def __init__(self, message: str | None=None):
        self.message = message or 'Resource not found'
        super().__init__(self.message)


class GUIError(Exception):
    def __init__(self, message: str | None=None):
        self.message = message or 'Unepected GUI error occurred'
        super().__init__(self.message)


class SummaryGenError(Exception):
    def __init__(self, message: str | None=None):
        self.message = message or 'An error occurred while generating the PDF'
        super().__init__(self.message)


class ElementJoinError(SummaryGenError):
    def __init__(self, message: str | None=None):
        self.message = message or 'An error occurred within a paragraph element'
        super().__init__(self.message)


class WidthExceededError(SummaryGenError):
    def __init__(self, message: str | None=None):
        self.message = message or 'Max width exceeded'
        super().__init__(self.message)
