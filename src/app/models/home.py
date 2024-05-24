class FrameModel:
    def __init__(self):
        self.offset: int = 0
        self.limit: int = 25
        self.current_items: list[str] = []
        self.cache: list[str] = []

    def increment_offset(self):
        self.offset += self.limit

    def decrement_offset(self):
        if self.offset < self.limit:
            self.offset = 0
        else:
            self.offset -= self.limit


class HomeModel:
    def __init__(self):
        self.__id_model = FrameModel()
        self.__version_model = FrameModel()
        self.selected_measure: str | None = None
        self.selected_versions: list[str] = []

    @property
    def id_limit(self) -> int:
        return self.__id_model.limit

    @id_limit.setter
    def id_limit(self, limit: int):
        self.__id_model.limit = limit

    @property
    def id_offset(self) -> int:
        return self.__id_model.offset

    @id_offset.setter
    def id_offset(self, offset: int):
        self.__id_model.offset = offset

    @property
    def version_limit(self) -> int:
        return self.__version_model.limit

    @version_limit.setter
    def version_limit(self, limit: int):
        self.__version_model.limit = limit

    @property
    def version_offset(self) -> int:
        return self.__version_model.offset

    @version_offset.setter
    def version_offset(self, offset: int):
        self.__version_model.offset = offset

    @property
    def measure_ids(self) -> list[str]:
        return self.__id_model.current_items

    @measure_ids.setter
    def measure_ids(self, items: list[str]):
        self.__id_model.current_items = items

    @property
    def measure_versions(self) -> list[str]:
        return self.__version_model.current_items

    @measure_versions.setter
    def measure_versions(self, items: list[str]):
        self.__version_model.current_items = items

    def increment_id_offset(self):
        self.__id_model.increment_offset()

    def decrement_id_offset(self):
        self.__id_model.decrement_offset()

    def increment_version_offset(self):
        self.__version_model.increment_offset()

    def decrement_version_offset(self):
        self.__version_model.decrement_offset()
