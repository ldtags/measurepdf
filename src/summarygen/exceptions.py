class SummaryGenError(Exception):
    def __init__(self, message: str | None=None):
        self.message = message or 'An error occurred while generating the PDF'
        super().__init__(self.message)


class ElementJoinError(SummaryGenError):
    def __init__(self, message: str | None=None):
        super().__init__(message or 'An error occurred within a paragraph element')


class WidthExceededError(SummaryGenError):
    def __init__(self, message: str | None=None):
        super().__init__(message or 'Max width exceeded')
