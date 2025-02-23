from reportlab.platypus import (
    Flowable,
    Spacer,
    KeepTogether,
    Paragraph,
    ListFlowable
)

from src.summarygen.styles import (
    INNER_HEIGHT,
    INNER_WIDTH
)


class BulletOption:
    def __init__(self, bullets: list[str]) -> None:
        self.bullets = bullets

    def get_bullet(self, level: int) -> str:
        if level < 1:
            level = 1

        return self.bullets[(level - 1) % len(self.bullets)]


class Story:
    def __init__(
        self,
        inner_height: float=INNER_HEIGHT,
        inner_width: float=INNER_WIDTH
    ) -> None:
        self.inner_height = inner_height
        self.inner_width = inner_width
        self.__contents: list[Flowable] = []

    @property
    def contents(self) -> list[Flowable]:
        _contents = self.__contents

        # trim any trailing space
        i = len(_contents) - 1
        while i > 0 and isinstance(_contents[i], Spacer):
            _contents.pop()
            i -= 1

        return _contents

    def get_height(self, flowable: Flowable) -> float:
        if isinstance(flowable, KeepTogether | ListFlowable):
            height = 0
            for item in flowable._content:
                height += self.get_height(item)
        elif isinstance(flowable, Paragraph):
            _, height = flowable.wrap(INNER_WIDTH, 0)
        else:
            _, height = flowable.wrap(0, 0)

        return height

    def add(self, *flowables: Flowable):
        for flowable in flowables:
            self.__contents.append(flowable)

    def clear(self):
        self.contents = []
        self.current_height = 0
