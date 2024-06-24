from __future__ import annotations
import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk

from src import utils
from src.app import styles, fonts
from src.app.ctkobjects import (
    ScrollableFrame,
    ScrollableCheckBoxFrame,
    SearchBar,
    PromptWindow,
    InfoPromptWindow,
    InputPromptWindow,
    FileDialogueWindow,
    ToolTip,
    Frame,
    Button,
    Toplevel
)


class HomePage(Frame):
    def __init__(self, parent: tk.Frame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid(row=0, column=0, sticky=tk.NSEW)

        self.parent = parent
        self.prompt: PromptWindow | None = None
        self.info_prompt: InfoPromptWindow | None = None
        self.yn_prompt: InputPromptWindow | None = None
        self.fd_prompt: FileDialogueWindow | None = None

        self.main_frame = MainFrame(self)
        self.main_frame.pack(side=tk.TOP,
                             anchor=tk.NW,
                             fill=tk.BOTH,
                             expand=True)

    @property
    def measure_id_list(self) -> MeasureListFrame:
        return self.main_frame.measure_id_list

    @property
    def measure_version_list(self) -> MeasureVersionsFrame:
        return self.main_frame.measure_version_list

    @property
    def measures_selection_list(self) -> SelectedMeasuresFrame:
        return self.main_frame.measures_selection_list

    def open_prompt(self, text: str):
        if self.prompt is None or not self.prompt.winfo_exists():
            self.prompt = PromptWindow(self, text)
        self.prompt.wm_transient(self.parent)
        self.prompt.focus()

    def update_prompt(self, text: str):
        if self.prompt is not None and self.prompt.winfo_exists():
            self.prompt.set_text(text)

    def run_prompt(self, func, *args):
        if self.prompt is not None and self.prompt.winfo_exists():
            self.after(1000, func, *args)
        self.prompt = None

    def close_prompt(self):
        if self.prompt is not None and self.prompt.winfo_exists():
            self.prompt.grab_release()
            self.prompt.destroy()
        self.prompt = None

    def open_yesno_prompt(self,
                          text: str,
                          ok_text: str='Ok',
                          cancel_txt: str='Cancel',
                          title=''):
        if self.yn_prompt is None or not self.yn_prompt.winfo_exists():
            self.yn_prompt = InputPromptWindow(self,
                                               text=text,
                                               ok_text=ok_text,
                                               cancel_text=cancel_txt,
                                               title=title)
        self.yn_prompt.wm_transient(self.parent)
        self.yn_prompt.focus()
        result = self.yn_prompt.get_result()
        self.yn_prompt = None
        return result

    def open_info_prompt(self,
                         text: str,
                         ok_text: str='Ok',
                         title: str='Info'):
        if self.info_prompt is None or not self.info_prompt.winfo_exists():
            self.info_prompt = InfoPromptWindow(self,
                                                text=text,
                                                ok_text=ok_text,
                                                title=title)
        self.info_prompt.wm_transient(self.parent)
        self.info_prompt.focus()
        self.info_prompt.wait()
        self.info_prompt = None

    def open_fd_prompt(self,
                       default_dest: str,
                       default_fname: str,
                       ok_text: str='Ok',
                       cancel_text: str='Cancel',
                       title: str=''
                      ) -> tuple[str, str, bool]:
        if self.fd_prompt is None or not self.fd_prompt.winfo_exists():
            self.fd_prompt = FileDialogueWindow(self,
                                                default_dest=default_dest,
                                                default_fname=default_fname,
                                                title=title,
                                                ok_text=ok_text,
                                                cancel_text=cancel_text)
        self.fd_prompt.wm_transient(self.parent)
        self.fd_prompt.focus()
        result = self.fd_prompt.get_result()
        self.fd_prompt = None
        return result


class MainFrame(Frame):
    def __init__(self, parent: tk.Frame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_columnconfigure((0, 1, 2),
                                  weight=1,
                                  uniform='HomePage')
        self.grid_rowconfigure((0), weight=1)

        self.measure_id_list = MeasureListFrame(self)
        self.measure_id_list.grid(row=0,
                                  column=0,
                                  sticky=ctk.NSEW,
                                  padx=(20, 20),
                                  pady=(20, 20))

        self.measure_version_list = MeasureVersionsFrame(self)
        self.measure_version_list.grid(row=0,
                                       column=1,
                                       sticky=ctk.NSEW,
                                       padx=(20, 20),
                                       pady=(20, 20))

        self.measures_selection_list = SelectedMeasuresFrame(self)
        self.measures_selection_list.grid(row=0,
                                          column=2,
                                          sticky=ctk.NSEW,
                                          padx=(20, 20),
                                          pady=(20, 20))


class MeasureListFrame(Frame):
    def __init__(self, parent: tk.Frame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.search_container = ctk.CTkFrame(self,
                                             fg_color=self._fg_color)
        self.search_container.grid(row=0,
                                   column=0,
                                   columnspan=3,
                                   sticky=tk.NSEW,
                                   padx=(10, 10),
                                   pady=(10, 10))

        self.search_bar = SearchBar(self.search_container,
                                    placeholder='Search for a measure...')
        self.search_bar.pack(side=tk.LEFT,
                             anchor=tk.NW,
                             fill=tk.BOTH,
                             expand=True,
                             padx=(0, 5))

        self.search_bar.update()
        img_size = tuple([self.search_bar.search_bar._current_height - 2] * 2)
        # filter_img = utils.get_tkimage(light_image='filter-black.png',
        #                                dark_image='filter-white.png',
        #                                size=img_size)
        # self.filter_btn = ctk.CTkButton(self.search_container,
        #                                 image=filter_img,
        #                                 height=img_size[1],
        #                                 width=img_size[0],
        #                                 text='',
        #                                 cursor='hand2')
        # self.filter_btn.pack(side=tk.LEFT,
        #                      anchor=tk.NW,
        #                      padx=(5, 0))
        reset_img = utils.get_tkimage(light_image='reset.png',
                                      size=img_size)
        self.reset_btn = ctk.CTkButton(self.search_container,
                                       image=reset_img,
                                       height=img_size[1],
                                       width=img_size[0],
                                       text='',
                                       cursor='hand2')
        self.reset_btn.pack(side=tk.LEFT,
                            anchor=tk.NW,
                            padx=(5, 0))

        self.measure_frame = ScrollableCheckBoxFrame(self)
        self.measure_frame.grid(row=1,
                                column=0,
                                columnspan=3,
                                sticky=tk.NSEW,
                                padx=(10, 10),
                                pady=(0, 10))

        self.back_btn = ctk.CTkButton(self,
                                      text='Back',
                                      state=tk.DISABLED,
                                      font=fonts.BODY)
        self.back_btn.grid(row=2,
                           column=0,
                           sticky=tk.SW,
                           padx=(10, 10),
                           pady=(0, 10))
        self.back_btn_tooltip = ToolTip(self.back_btn,
                                        'View the previous 25 measures')

        self.next_btn = ctk.CTkButton(self,
                                      text='Next',
                                      font=fonts.BODY)
        self.next_btn.grid(row=2,
                           column=2,
                           sticky=tk.SE,
                           padx=(10, 10),
                           pady=(0, 10))
        self.next_btn_tooltip = ToolTip(self.next_btn,
                                        'View the next 25 measures')

    @property
    def measure_ids(self) -> list[str]:
        return self.measure_frame.items

    @measure_ids.setter
    def measure_ids(self, items: list[str]):
        self.measure_frame.items = items

    @property
    def selected_measures(self) -> list[str]:
        return self.measure_frame.selected_items

    @selected_measures.setter
    def selected_measures(self, items: list[str]):
        self.measure_frame.selected_items = items


class MeasureVersionsFrame(Frame):
    def __init__(self, parent: tk.Frame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure((0), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.search_bar = SearchBar(self,
                                    placeholder='Search for a version...')
        self.search_bar.grid(row=0,
                             column=0,
                             columnspan=3,
                             sticky=tk.NSEW,
                             padx=(10, 10),
                             pady=(10, 10))

        self.version_frame = ScrollableCheckBoxFrame(self)
        self.version_frame.grid(row=1,
                                column=0,
                                columnspan=3,
                                sticky=tk.NSEW,
                                padx=(10, 10),
                                pady=(0, 10))

    @property
    def versions(self) -> list[str]:
        return self.version_frame.items

    @versions.setter
    def versions(self, items: list[str]):
        self.version_frame.clear()
        for item in items:
            font = styles.DEF_FONT
            if len(item.split('-')) == 2:
                font = (*font, 'bold')
            self.version_frame.add_item(item, font=font)

    @property
    def selected_versions(self) -> list[str]:
        return self.version_frame.selected_items

    @selected_versions.setter
    def selected_versions(self, items: list[str]):
        self.version_frame.selected_items = items


class SelectedMeasuresFrame(Frame):
    def __init__(self, master: tk.Frame, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0), weight=1)
        self.grid_columnconfigure((1, 2), weight=1)

        self.search_bar = SearchBar(self,
                                    placeholder='Add a measure...')
        self.search_bar.grid(row=0,
                             column=0,
                             columnspan=3,
                             sticky=tk.NSEW,
                             padx=(10, 10),
                             pady=(10, 10))

        self.measures_frame = ScrollableFrame(self)
        self.measures_frame.grid(row=1,
                                 column=0,
                                 columnspan=3,
                                 sticky=tk.NSEW,
                                 padx=(10, 10),
                                 pady=(0, 10))

        self.clear_btn = ctk.CTkButton(self,
                                       text='Clear Selections',
                                       fg_color='#FF0000',
                                       hover_color='#D50000',
                                       cursor='hand2',
                                       state='disabled')
        self.clear_btn.grid(row=2,
                            column=0,
                            sticky=tk.NSEW,
                            padx=(10, 10),
                            pady=(0, 10))
        self.clear_tooltip = ToolTip(self.clear_btn,
                                     message='Unselects all selected'
                                             ' measure versions')

        self.add_btn = ctk.CTkButton(self,
                                     text='Create PDF',
                                     state='disabled')
        self.add_btn.grid(row=2,
                          column=1,
                          columnspan=2,
                          sticky=tk.NSEW,
                          padx=(10, 10),
                          pady=(0, 10))
        self.add_tooltip = ToolTip(self.add_btn,
                                   message='Creates a summary PDF'
                                           ' with all selected measures')

    @property
    def measures(self) -> list[str]:
        return self.measures_frame.items

    @measures.setter
    def measures(self, items: list[str]):
        self.measures_frame.items = items
