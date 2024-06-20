import customtkinter as ctk

from src import utils
from src.app.ctkobjects.tooltip import ToolTip


class SearchBar(ctk.CTkFrame):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 placeholder: str,
                 include_search_btn: bool=False,
                 include_reset_btn: bool=False,
                 include_add_btn: bool=False,
                 search_tooltip: str | None=None,
                 reset_tooltip: str | None=None,
                 add_tooltip: str | None=None,
                 **kwargs):
        kwargs['fg_color'] = kwargs.get('fg_color', parent._fg_color)
        super().__init__(parent, **kwargs)

        self.placeholder = placeholder

        entry_width = 10
        if include_search_btn:
            entry_width -= 1
        if include_reset_btn:
            entry_width -= 1
        if include_add_btn:
            entry_width -= 1

        self.grid_rowconfigure((1), weight=1)
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_columnconfigure((2), weight=1)

        self.search_bar = ctk.CTkEntry(self,
                                       placeholder_text=placeholder)
        self.search_bar.grid(row=0,
                             column=0,
                             columnspan=entry_width,
                             sticky=ctk.NSEW,
                             padx=(0, 0))

        if include_search_btn:
            self.search_btn = ctk.CTkButton(self,
                                            text='',
                                            image=utils.get_tkimage(
                                                'search.png',
                                                size=(24, 24)),
                                            width=parent.winfo_width() / 8)
            self.search_btn.grid(row=0,
                                 column=entry_width,
                                 padx=(5, 0))
            if search_tooltip != None:
                self.search_tooltip = ToolTip(self.search_btn,
                                              message=search_tooltip)
            entry_width += 1

        if include_reset_btn:
            self.reset_btn = ctk.CTkButton(self,
                                           text='',
                                           image=utils.get_tkimage(
                                                'reset.png',
                                                size=(24, 24)),
                                           width=parent.winfo_width() / 8)
            self.reset_btn.grid(row=0,
                                column=entry_width,
                                padx=(5, 0))
            if reset_tooltip != None:
                self.reset_tooltip = ToolTip(self.reset_btn,
                                             message=reset_tooltip)
            entry_width += 1

        if include_add_btn:
            self.add_btn = ctk.CTkButton(self,
                                         text='',
                                         image=utils.get_tkimage(
                                                'plus.png',
                                                size=(24, 24)),
                                         width=parent.winfo_width() / 8)
            self.add_btn.grid(row=0,
                              column=entry_width,
                              padx=(5, 0))
            if add_tooltip != None:
                self.add_tooltip = ToolTip(self.add_btn,
                                           message=add_tooltip)
            entry_width += 1

    def get(self) -> str:
        return self.search_bar.get()

    def clear(self):
        self.search_bar.delete(0, ctk.END)
        self.search_bar.configure(placeholder_text=self.placeholder)
