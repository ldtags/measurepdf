import customtkinter as ctk

from src.app import styles
from src.app.ctkobjects import (
    ScrollableFrame,
    ScrollableCheckBoxFrame,
    ScrollableRadioButtonFrame,
    SearchBar,
    PromptWindow,
    InfoPromptWindow,
    InputPromptWindow,
    FileDialogueWindow,
    ToolTip
)


class HomePage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid(row=0, column=0, sticky=ctk.NSEW)
        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.parent = parent
        self.prompt: PromptWindow | None = None
        self.info_prompt: InfoPromptWindow | None = None
        self.yn_prompt: InputPromptWindow | None = None
        self.fd_prompt: FileDialogueWindow | None = None

        self.measure_id_list = MeasureListFrame(self,
                                                fg_color=self._fg_color)
        self.measure_id_list.grid(row=0,
                                  rowspan=3,
                                  column=0,
                                  sticky=ctk.NSEW,
                                  padx=(20, 20),
                                  pady=(20, 20))

        self.measure_version_list \
            = MeasureVersionsFrame(self, fg_color=self._fg_color)
        self.measure_version_list.grid(row=0,
                                       rowspan=3,
                                       column=1,
                                       sticky=ctk.NSEW,
                                       padx=(20, 20),
                                       pady=(20, 20))

        self.measures_selection_list \
            = SelectedMeasuresFrame(self, fg_color=self._fg_color)
        self.measures_selection_list.grid(row=0,
                                          rowspan=3,
                                          column=2,
                                          sticky=ctk.NSEW,
                                          padx=(20, 20),
                                          pady=(20, 20))

    def open_prompt(self, text: str):
        if self.prompt is None or not self.prompt.winfo_exists():
            self.prompt = PromptWindow(self, text)
        self.prompt.wm_transient(self.parent)
        self.prompt.focus()

    def close_prompt(self):
        if self.prompt is not None and self.prompt.winfo_exists():
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


class MeasureListFrame(ctk.CTkFrame):
    def __init__(self, parent: HomePage, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.search_bar = SearchBar(self,
                                    placeholder='Search for a measure...',
                                    include_search_btn=True,
                                    include_reset_btn=True,
                                    search_tooltip='Search for a'
                                                   ' measure by entering that'
                                                   ' measure\'s statewide id'
                                                   ' (i.e., SWAP001)',
                                    reset_tooltip='Reset the currently shown'
                                                  ' measures')
        self.search_bar.grid(row=0,
                             column=0,
                             columnspan=3,
                             sticky=ctk.NSEW,
                             padx=(10, 10),
                             pady=(10, 10))

        self.measure_frame = ScrollableRadioButtonFrame(self)
        self.measure_frame.grid(row=1,
                                column=0,
                                columnspan=3,
                                sticky=ctk.NSEW,
                                padx=(10, 10))

        self.back_btn = ctk.CTkButton(self,
                                      text='<<')
        self.back_btn.grid(row=2,
                           column=0,
                           sticky=ctk.SW,
                           padx=(10, 10),
                           pady=(10, 10))

        self.next_btn = ctk.CTkButton(self,
                                      text='>>')
        self.next_btn.grid(row=2,
                           column=2,
                           sticky=ctk.SE,
                           padx=(10, 10),
                           pady=(10, 10))

    @property
    def measure_ids(self) -> list[str]:
        return self.measure_frame.items

    @measure_ids.setter
    def measure_ids(self, items: list[str]):
        self.measure_frame.items = items

    @property
    def selected_measure(self) -> str | None:
        return self.measure_frame.selected_item

    @selected_measure.setter
    def selected_measure(self, item: str | None):
        self.measure_frame.selected_item = item


class MeasureVersionsFrame(ctk.CTkFrame):
    def __init__(self, parent: HomePage, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure((0), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0), weight=1)

        self.search_bar = SearchBar(self,
                                    placeholder='Search for a version...',
                                    include_search_btn=True,
                                    include_reset_btn=True,
                                    search_tooltip='Search for one of the'
                                                   ' currently selected'
                                                   ' measure\'s versions by'
                                                   ' entering the full version'
                                                   ' id (i.e., SWAP001-03)',
                                    reset_tooltip='Reset the measure versions'
                                                  ' shown below to all of the'
                                                  ' selected measure\'s'
                                                  ' versions')
        self.search_bar.grid(row=0,
                             column=0,
                             sticky=ctk.NSEW,
                             padx=(10, 10),
                             pady=(10, 10))

        self.version_frame = ScrollableCheckBoxFrame(self)
        self.version_frame.grid(row=1,
                                column=0,
                                sticky=ctk.NSEW,
                                padx=(10, 10),
                                pady=(0, 10))

    @property
    def versions(self) -> list[str]:
        return self.version_frame.items

    @versions.setter
    def versions(self, items: list[str]):
        self.version_frame.clear()
        for item in items:
            font = (styles.FONT_NAME, styles.FONT_SIZE)
            if len(item.split('-')) == 2:
                font = (*font, 'bold')
            self.version_frame.add_item(item, font=font)

    @property
    def selected_versions(self) -> list[str]:
        return self.version_frame.selected_items

    @selected_versions.setter
    def selected_versions(self, items: list[str]):
        self.version_frame.selected_items = items


class SelectedMeasuresFrame(ctk.CTkFrame):
    def __init__(self, master: HomePage, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0), weight=0)
        self.grid_columnconfigure((1, 2), weight=0)

        self.search_bar = SearchBar(self,
                                    placeholder='Add a measure...',
                                    include_add_btn=True,
                                    add_tooltip='Select a measure version'
                                                ' by entering a full measure'
                                                ' id (i.e., SWAP001-03)')
        self.search_bar.grid(row=0,
                             column=0,
                             columnspan=3,
                             sticky=ctk.NSEW,
                             padx=(10, 10),
                             pady=(10, 10))

        self.measures_frame = ScrollableFrame(self)
        self.measures_frame.grid(row=1,
                                 column=0,
                                 columnspan=3,
                                 sticky=ctk.NSEW,
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
                            sticky=ctk.NSEW,
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
                          sticky=ctk.NSEW,
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
