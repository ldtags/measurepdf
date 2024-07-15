"""Error classes for package-specific exceptions."""


from src.etrm.exceptions import *


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
