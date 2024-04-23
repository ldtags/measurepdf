import customtkinter as ctk
from typing import Callable, Type, TypeVar, Generic


T = TypeVar('T', bound=ctk.CTkBaseClass)


class ScrollableFrame(ctk.CTkScrollableFrame, Generic[T]):
    def __init__(self,
                 master: ctk.CTkFrame,
                 element_type: Type[T] = ctk.CTkLabel,
                 element_pady: tuple[int, int] = (0, 5),
                 element_padx: tuple[int, int] = (0, 0),
                 command: Callable[[], None] | None=None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self.elements: list[T] = []
        self.element_type = element_type
        self.element_pady = element_pady
        self.element_padx = element_padx
        self.command = command

    def place(self, element: T, row: int):
        element.grid(row=row,
                     column=0,
                     pady=self.element_pady,
                     padx=self.element_padx)

    def remove_item(self, item: str):
        index = -1
        for i, element in enumerate(self.elements):
            if item == element.cget('text'):
                element.destroy()
                self.elements.remove(element)
                index = i
                break

        if index == -1 or len(self.elements) == 0:
            return

        for i in range(index, len(self.elements)):
            self.place(self.elements[i], i)

    def clear(self):
        for item in self.elements:
            item.destroy()
        self.elements.clear()

    def add_item(self, item: str, **kwargs):
        element = self.element_type(self, text=item, **kwargs)
        self.place(element, len(self.elements))
        if self.command is not None:
            element.configure(command=self.command)
        self.elements.append(element)

    def get_element(self, item: str) -> T | None:
        for element in self.elements:
            if item == element.cget('text'):
                return element
        return None

    def set_command(self, command: Callable[[], None]):
        self.command = command
        for element in self.elements:
            element.configure(command=command)

    @property
    def items(self) -> list[str]:
        return list(map(lambda element: element.cget('text'), self.elements))

    @items.setter
    def items(self, item_list: list[str]):
        self.clear()
        for item in item_list:
            self.add_item(item)


class ScrollableCheckBoxFrame(ScrollableFrame[ctk.CTkCheckBox]):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 command: Callable[[], None] | None=None,
                 **kwargs):
        super().__init__(parent,
                         ctk.CTkCheckBox,
                         element_pady=(0, 10),
                         command=command,
                         **kwargs)

    @property
    def selected_items(self) -> list[str]:
        return [checkbox.cget('text')
            for checkbox in self.elements
            if checkbox.get() == 1]

    @selected_items.setter
    def selected_items(self, items: list[str]):
        for checkbox in self.elements:
            item = checkbox.cget('text')
            if item in items:
                checkbox.select()
            else:
                checkbox.deselect()


class ScrollableRadioButtonFrame(ScrollableFrame[ctk.CTkRadioButton]):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 command: Callable[[], None] | None=None,
                 **kwargs):
        super().__init__(parent,
                         ctk.CTkRadioButton,
                         element_pady=(0, 10),
                         command=command,
                         **kwargs)
        self.rbvar = ctk.StringVar()

    def add_item(self, item: str, selected: bool=False):
        super().add_item(item, value=item, variable=self.rbvar)
        if selected:
            self.selected_item = item

    @property
    def selected_item(self) -> str | None:
        item = self.rbvar.get()
        if item == '':
            return None
        return item

    @selected_item.setter
    def selected_item(self, item: str | None):
        radio_button = self.get_element(self.selected_item)
        if radio_button != None:
            radio_button.deselect()

        if item != None:
            radio_button = self.get_element(item)
            if radio_button != None:
                radio_button.select()
