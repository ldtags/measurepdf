"""Error classes for package-specific exceptions."""


class GUIError(Exception):
    def __init__(self, message: str | None=None):
        self.message = message or 'Unepected GUI error occurred'
        super().__init__(self.message)
