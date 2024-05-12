import customtkinter as ctk

from src.app.ctkobjects import (
    ScrollableFrame,
    ScrollableCheckBoxFrame,
    ScrollableRadioButtonFrame,
    SearchBar
)


class HomePage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid(row=0, column=0, sticky=ctk.NSEW)
        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.measure_id_list = MeasureListFrame(self,
                                                fg_color=self._fg_color)
        self.measure_id_list.grid(row=0,
                                  rowspan=3,
                                  column=0,
                                  sticky=ctk.NSEW,
                                  padx=(20, 20),
                                  pady=(20, 20))

        self.measure_version_list = MeasureVersionsFrame(self,
                                                         fg_color=self._fg_color)
        self.measure_version_list.grid(row=0,
                                       rowspan=3,
                                       column=1,
                                       sticky=ctk.NSEW,
                                       padx=(20, 20),
                                       pady=(20, 20))

        self.measures_selection_list = SelectedMeasuresFrame(self,
                                                             fg_color=self._fg_color)
        self.measures_selection_list.grid(row=0,
                                          rowspan=3,
                                          column=2,
                                          sticky=ctk.NSEW,
                                          padx=(20, 20),
                                          pady=(20, 20))


class MeasureListFrame(ctk.CTkFrame):
    def __init__(self, parent: HomePage, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure((0, 2), weight=0)
        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.search_bar = SearchBar(self,
                                    placeholder='Search for a measure...',
                                    include_search_btn=True,
                                    include_reset_btn=True)
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
                                    include_reset_btn=True)
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
        self.version_frame.items = items

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
                                    include_add_btn=True)
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
                                       cursor='hand2')
        self.clear_btn.grid(row=2,
                            column=0,
                            sticky=ctk.NSEW,
                            padx=(10, 10),
                            pady=(0, 10))

        self.add_btn = ctk.CTkButton(self,
                                     text='Create PDF')
        self.add_btn.grid(row=2,
                          column=1,
                          columnspan=2,
                          sticky=ctk.NSEW,
                          padx=(10, 10),
                          pady=(0, 10))

    @property
    def measures(self) -> list[str]:
        return self.measures_frame.items

    @measures.setter
    def measures(self, items: list[str]):
        self.measures_frame.items = items
