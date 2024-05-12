"""Error classes for package-specific exceptions."""

class ETRMRequestError(Exception):
    def __init__(self, message: str | None=None):
        self.message = message or 'Request to the eTRM database failed'
        super().__init__(self.message)
        

class ETRMResponseError(Exception):
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
