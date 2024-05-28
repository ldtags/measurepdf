class HomeModel:
    """MVC model for the Home module."""

    def __init__(self):
        self.offset: int = 0
        self.limit: int = 25
        self.measure_ids: list[str] = []
        self.measure_versions: list[str] = []
        self.selected_measure: str | None = None
        self.selected_versions: list[str] = []

    def increment_offset(self):
        self.offset += self.limit

    def decrement_offset(self):
        if self.offset < self.limit:
            self.offset = 0
        else:
            self.offset -= self.limit
