class HomeModel:
    """MVC model for the Home module."""

    def __init__(self):
        self.offset: int = 0
        self.limit: int = 25
        self.count: int = 0
        self.use_category: str | None = None
        self.measure_ids: list[str] = []
        self.measure_versions: dict[str, list[str]] = {}
        self.selected_measures: list[str] = []
        self.selected_versions: list[str] = []

    @property
    def all_versions(self) -> list[str]:
        _all_versions: list[str] = []
        for _, versions in self.measure_versions.items():
            _all_versions.extend(versions)
        return _all_versions

    def increment_offset(self):
        if self.offset + self.limit > self.count:
            self.offset = self.count - self.limit
        else:
            self.offset += self.limit

    def decrement_offset(self):
        if self.offset < self.limit:
            self.offset = 0
        else:
            self.offset -= self.limit
