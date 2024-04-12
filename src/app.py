from abc import abstractmethod
import os
import re
import customtkinter as ctk
from typing import Type, Callable
from configparser import ConfigParser

from src import _ROOT
from src.etrm import ETRMConnection
from src._exceptions import (
    UnauthorizedError,
    GUIError
)


ctk.set_appearance_mode('system')
ctk.set_default_color_theme('dark-blue')


class Page(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, **kwargs):
        super().__init__(parent, **kwargs)

    @abstractmethod
    def show(self):
        ...


class AppController(ctk.CTk):
    def __init__(self, width: int = 1100, height: int = 580):
        super().__init__()

        self.connection: ETRMConnection | None = None
        self.selected_measure: str | None = None
        self.selected_measures: list[str] = []

        self.title('  eTRM Measure(s) to PDF')
        self.geometry(f'{width}x{height}')

        container = ctk.CTkFrame(self)
        container.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames: dict[Type[Page], Page] = {}

        for f_class in (AuthFrame, MainFrame, ResultsFrame):
            frame = f_class(container, self)
            self.frames[f_class] = frame
            frame.grid(row=0, column=0, sticky=ctk.NSEW)

    def connect(self, auth_token: str):
        self.connection = ETRMConnection(auth_token)

    def set_measures(self, ids: list[str]):
        self.measure_ids = ids

    def get_measures(self, offset: int = 0, limit: int = 25) -> list[str]:
        if self.connection == None:
            raise UnauthorizedError()

        return self.connection.get_measure_ids(offset, limit)

    def get_versions(self,
                     measure_id: str,
                     offset: int = 0,
                     limit: int = 25
                    ) -> list[str]:
        """Retrieves all versions of the measure with ID `measure_id`."""

        if self.connection == None:
            raise UnauthorizedError()

        return self.connection.get_measure_versions(measure_id, offset, limit)

    def show_frame(self, f_class: Type[Page]):
        frame = self.frames[f_class]
        frame.show()

    def nav_results(self):
        self.show_frame(ResultsFrame)

    def on_close(self):
        if self.connection != None:
            self.connection.close()

    def run(self, run_mode: str='client'):
        match run_mode:
            case 'client':
                self.show_frame(AuthFrame)
            case 'dev':    
                config = ConfigParser()
                config.read(os.path.join(_ROOT, 'config.ini'))
                self.connect(config['etrm']['type'] + ' ' + config['etrm']['token'])
                frame: MainFrame = self.frames[MainFrame]
                frame.add_measures()
                self.show_frame(MainFrame)
            case _:
                raise GUIError(f'unknown run mode - {run_mode}')

        self.mainloop()

        if self.connection != None:
            self.connection.close()
            self.connection = None


def _validate_token_input_char(_input: str | None=None) -> bool:
    if _input is None or _input == '':
        return True

    if not re.fullmatch('^[a-zA-Z0-9 ]$', _input):
        return False

    return True


class AuthFrame(Page):
    def __init__(self, parent: ctk.CTkFrame, controller: AppController, **kwargs):
        super().__init__(parent, **kwargs)

        self.vtichar = self.register(_validate_token_input_char)

        self.controller = controller

        container = ctk.CTkFrame(self)
        container.pack(anchor=ctk.CENTER, expand=True)
        container.grid_rowconfigure((0, 3), weight=1)
        container.grid_rowconfigure((1, 2), weight=0)
        container.grid_columnconfigure(0, weight=1)

        self.auth_label = ctk.CTkLabel(container,
                                       text='eTRM Authorization Token:')
        self.auth_label.grid(row=0,
                             column=0,
                             sticky=ctk.S,
                             pady=(10, 2),
                             padx=(15, 15))

        self.auth_input = ctk.CTkEntry(container,
                                       width=200,
                                       placeholder_text='Token 12c45b73a0b...',
                                       validatecommand=self.vtichar,
                                       validate='key')
        self.auth_input.grid(row=1,
                             column=0,
                             pady=(2, 2),
                             padx=(15, 15))

        self.err_label = ctk.CTkLabel(container,
                                      width=200,
                                      wraplength=200,
                                      text='',
                                      text_color='red')

        self.auth_btn = ctk.CTkButton(container,
                                      text='Continue',
                                      command=self.auth_btn_onclick)
        self.auth_btn.grid(row=3,
                           column=0,
                           sticky=ctk.N,
                           pady=(10, 13),
                           padx=(15, 15))

        self.bind('<Button-1>', lambda _: self.focus_set())
        container.bind('<Button-1>', lambda _: self.focus_set())
        self.auth_label.bind('<Button-1>', lambda _: self.auth_label.focus_set())
        self.auth_btn.bind('<Button-1>', lambda _: self.auth_btn.focus_set())
        self.err_label.bind('<Button-1>', lambda _: self.err_label.focus_set())

    def show(self):
        if self.controller.connection != None:
            self.auth_input.delete(0, ctk.END)
            self.auth_input.insert(0, self.controller.connection.auth_token)

        self.tkraise()

    def display_err(self, err_msg: str):
        self.err_label.grid(row=2, column=0, pady=(2, 2), padx=(15, 15))
        self.err_label.configure(text=err_msg)

    def auth_btn_onclick(self):
        token_header = 'Token'
        token = self.auth_input.get()
        if token == '':
            self.display_err('Please enter an auth token...')
            return
            
        if ' ' in token:
            split_token = token.split(' ')
            if len(split_token) > 2:
                self.display_err(f'Invalid auth token format: {token}')
                return

            if split_token[0].lower() != token_header.lower():
                self.display_err(f'Invalid token header: {split_token[0]}')
                return

            token = split_token[1]

        if not re.fullmatch('^[a-zA-Z0-9]+$', token):
            self.display_err(f'Invalid auth token: {token}')
            return

        self.controller.connect(f'{token_header} {token}')
        main_frame: MainFrame = self.controller.frames[MainFrame]
        try:
            main_frame.show()
        except UnauthorizedError:
            self.display_err('Unauthorized token')


class MainFrame(Page):
    def __init__(self, parent: ctk.CTkFrame, controller: AppController, **kwargs):
        super().__init__(parent, **kwargs)

        self.controller = controller

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.measure_list = MeasureListFrame(self, controller)
        self.measure_list.grid(row=1,
                               column=0,
                               sticky=ctk.NSEW)

        self.measure_versions = MeasureVersionsFrame(self, controller)
        self.measure_versions.grid(row=1,
                                   column=1,
                                   sticky=ctk.NSEW)

        self.back_btn = ctk.CTkButton(self,
                                      text='Reset Auth Token',
                                      command=self.nav_auth)
        self.back_btn.grid(row=0,
                           column=2,
                           sticky=ctk.NSEW,
                           padx=(10, 10),
                           pady=(10, 10))

        self.measures_selected = SelectedMeasuresFrame(self)
        self.measures_selected.grid(row=1,
                                    column=2,
                                    sticky=ctk.NSEW,
                                    padx=(10, 10),
                                    pady=(10, 10))

        self.add_btn = ctk.CTkButton(self,
                                     text='Create PDF',
                                     command=self.nav_results)
        self.add_btn.grid(row=2,
                          column=2,
                          sticky=ctk.NSEW,
                          padx=(10, 10),
                          pady=(10, 10))

    def show(self):
        if self.controller.connection == None:
            raise UnauthorizedError()

        if self.measure_list.is_empty():
            measures = self.controller.get_measures()
            self.measure_list.add_measures(measures)

        self.tkraise()

    def add_measures(self, offset: int = 0, limit: int = 25):
        measure_ids = self.controller.get_measures(offset, limit)
        self.measure_list.add_measures(measure_ids)

    def select_measure(self, _id: str):
        versions = self.controller.get_versions(_id)
        self.measure_versions.clear_versions()
        self.measure_versions.add_versions(versions)
        self.controller.selected_measure = _id

    def add_selections(self, versions: str):
        for version in versions:
            if version not in self.controller.selected_measures:
                self.controller.selected_measures.append(version)
                self.measures_selected.add_version(version)

    def remove_selections(self, versions: str):
        for version in versions:
            if version in self.controller.selected_measures:
                self.controller.selected_measures.remove(version)
                self.measures_selected.remove_version(version)

    def nav_auth(self):
        self.controller.show_frame(AuthFrame)

    def nav_results(self):
        self.controller.show_frame(ResultsFrame)


class MeasureListFrame(ctk.CTkFrame):
    def __init__(self, parent: MainFrame, controller: AppController, **kwargs):
        super().__init__(parent, **kwargs)

        self.controller = controller
        self.parent = parent

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.measure_frame = ScrollableRadiobuttonFrame(self, self.select_measure)
        self.measure_frame.grid(row=1,
                                column=0,
                                columnspan=3,
                                sticky=ctk.NSEW)

        back_btn = ctk.CTkButton(self,
                                 text='<<')
        back_btn.grid(row=2,
                      column=0,
                      sticky=ctk.SW)

        next_btn = ctk.CTkButton(self,
                                 text='>>')
        next_btn.grid(row=2,
                      column=2,
                      sticky=ctk.SE)

    def select_measure(self):
        self.parent.select_measure(self.measure_frame.get_checked_item())

    def add_measures(self, ids: list[str]):
        for measure_id in ids:
            self.measure_frame.add_item(measure_id)

    def is_empty(self):
        return len(self.measure_frame.radiobutton_list) == 0


class ScrollableRadiobuttonFrame(ctk.CTkScrollableFrame):
    def __init__(self,
                 master: MeasureListFrame,
                 command: Callable[[], None] | None=None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self.command = command
        self.radiobutton_variable = ctk.StringVar()
        self.radiobutton_list: list[ctk.CTkRadioButton] = []

    def remove_item(self, checkbox: ctk.CTkRadioButton):
        for radiobutton in self.radiobutton_list:
            if checkbox == radiobutton:
                radiobutton.destroy()
                self.radiobutton_list.remove(radiobutton)
                return

    def clear_items(self):
        for radiobutton in self.radiobutton_list:
            radiobutton.destroy()
        self.radiobutton_list.clear()

    def add_item(self, item: str):
        radiobutton = ctk.CTkRadioButton(self,
                                         text=item,
                                         value=item,
                                         variable=self.radiobutton_variable)
        if self.command is not None:
            radiobutton.configure(command=self.command)

        radiobutton.grid(row=len(self.radiobutton_list),
                         column=0,
                         pady=(0, 10))

        self.radiobutton_list.append(radiobutton)

    def get_checked_item(self) -> str:
        return self.radiobutton_variable.get()


class MeasureVersionsFrame(ctk.CTkFrame):
    def __init__(self, parent: MainFrame, controller: AppController, **kwargs):
        super().__init__(parent, **kwargs)

        self.parent = parent
        self.controller = controller

        self.grid_rowconfigure((0), weight=1)
        self.grid_columnconfigure((0), weight=1)

        self.version_frame = ScrollableCheckBoxFrame(self,
                                                     command=self.select_version)
        self.version_frame.grid(row=0,
                                column=0,
                                sticky=ctk.NSEW)

    def _is_selected(self, version: str) -> bool:
        return version in self.controller.selected_measures

    def select_version(self):
        new_versions = list(
            filter(lambda version: not self._is_selected(version),
                   self.version_frame.get_checked_items()))
        self.parent.add_selections(new_versions)

        extra_versions = list(
            filter(lambda version: self._is_selected(version),
                   self.version_frame.get_unchecked_items()))
        self.parent.remove_selections(extra_versions)

    def add_versions(self, versions: list[str]):
        for version in versions:
            self.version_frame.add_item(version)
            if version in self.controller.selected_measures:
                checkbox = self.version_frame.get_element(version)
                if checkbox == None:
                    raise GUIError(f'{version} is not a selected measure')
                checkbox.select()

    def clear_versions(self):
        self.version_frame.clear_items()


class ScrollableCheckBoxFrame(ctk.CTkScrollableFrame):
    def __init__(self,
                 parent: MeasureVersionsFrame,
                 command: Callable[[], None] | None=None,
                 **kwargs):
        super().__init__(parent, **kwargs)

        self.parent = parent
        self.command = command
        self.checkbox_list: list[ctk.CTkCheckBox] = []

    def add_item(self, item: str):
        checkbox = ctk.CTkCheckBox(self, text=item)
        if self.command is not None:
            checkbox.configure(command=self.command)

        checkbox.grid(row=len(self.checkbox_list),
                      column=0,
                      pady=(0, 10))

        self.checkbox_list.append(checkbox)

    def remove_item(self, item: str):
        for checkbox in self.checkbox_list:
            if item == checkbox.cget('text'):
                checkbox.destroy()
                self.checkbox_list.remove(checkbox)
                return

    def clear_items(self):
        for checkbox in self.checkbox_list:
            checkbox.destroy()
        self.checkbox_list.clear()

    def get_element(self, item: str) -> ctk.CTkCheckBox | None:
        for checkbox in self.checkbox_list:
            if item == checkbox.cget('text'):
                return checkbox
        return None

    def get_checked_items(self) -> list[str]:
        return [checkbox.cget('text')
                    for checkbox in self.checkbox_list
                    if checkbox.get() == 1]

    def get_unchecked_items(self) -> list[str]:
        return [checkbox.cget('text')
                    for checkbox in self.checkbox_list
                    if checkbox.get() == 0]


class SelectedMeasuresFrame(ctk.CTkScrollableFrame):
    def __init__(self, master: MainFrame, **kwargs):
        super().__init__(master, **kwargs)

        self.item_list: list[ctk.CTkLabel] = []

    def place_item(self, item: ctk.CTkLabel, row: int):
        item.grid(row=row,
                  column=0,
                  pady=(0, 5))

    def add_version(self, version: str):
        label = ctk.CTkLabel(self, text=version)
        print(f'inserting {version} at row {len(self.item_list)}')
        self.place_item(label, len(self.item_list))
        self.item_list.append(label)

    def remove_version(self, version: str):
        version_index = -1
        for i, item in enumerate(self.item_list):
            if version == item._text:
                item.destroy()
                self.item_list.remove(item)
                version_index = i
                break

        if version_index == -1 or len(self.item_list) == 0:
            return

        for i in range(version_index, len(self.item_list)):
            item = self.item_list[i]
            self.place_item(item, i)

    def remove_versions(self, versions: list[str]):
        for version in versions:
            self.remove_version(version)

    def clear_items(self):
        for item in self.item_list:
            item.destroy()
        self.item_list.clear()

    def set_versions(self, items: list[str]):
        self.clear_items()
        for item in items:
            self.add_version(item)


class ResultsFrame(Page):
    def __init__(self, parent: ctk.CTkFrame, controller: AppController, **kwargs):
        super().__init__(parent, **kwargs)

        self.controller = controller

    def show(self):
        pass
