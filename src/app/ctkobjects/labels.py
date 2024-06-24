import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Literal

from src.app import fonts
from src.app.ctkobjects import Frame
from src.exceptions import GUIError


class OptionLabel(Frame):
    def __init__(self,
                 parent: tk.Frame,
                 title: str,
                 sub_title: str,
                 level: Literal[0, 1]=0,
                 **kwargs):
        super().__init__(parent, **kwargs)

        sub_title_font = fonts.BODY
        match level:
            case 0:
                title_font = fonts.SUB_HEADER
            case 1:
                title_font = fonts.BODY_BOLD
            case x:
                raise GUIError(f'Invalid precedence level: {x}')

        self.title = ctk.CTkLabel(self,
                                  text=title,
                                  font=title_font)
        self.title.grid(row=0,
                        column=0,
                        sticky=tk.NW)

        self.sub_title = ctk.CTkLabel(self,
                                      text=sub_title,
                                      font=sub_title_font)
        self.sub_title.grid(row=1,
                            column=0,
                            sticky=tk.NW)

        if level == 0:
            self.separator = ttk.Separator(self)
            self.separator.grid(row=2,
                                column=0,
                                sticky=tk.NSEW,
                                padx=(0, 0),
                                pady=(5, 5))

        self.title.bind('<Configure>', lambda _: self.rewrap(self.title))
        self.sub_title.bind('<Configure>',
                            lambda _: self.rewrap(self.sub_title))

    def rewrap(self, label: tk.Label):
        label.config(wraplength=self.parent.winfo_width())
