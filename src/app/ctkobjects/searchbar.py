import tkinter as tk
import customtkinter as ctk

from src import utils
from src.app import fonts
from src.app.ctkobjects.frames import Frame


class SearchBar(Frame):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 placeholder: str='',
                 **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(fg_color=parent._fg_color,
                       height=fonts.BODY[1])

        self.placeholder = placeholder

        try:
            _theme = ctk.ThemeManager.theme['CTkEntry']
            if not isinstance(_theme, dict):
                raise KeyError
        except KeyError:
            _theme = {}

        _fg_color = _theme.get('fg_color', self._fg_color)
        _border_color = _theme.get('border_color', self._border_color)
        _corner_radius = _theme.get('corder_radius', self._corner_radius)
        _border_width = _theme.get('border_width', self._border_width)
        self.container = ctk.CTkFrame(self,
                                      fg_color=_fg_color,
                                      border_color=_border_color,
                                      corner_radius=_corner_radius,
                                      border_width=_border_width)
        self.container.pack(side=tk.TOP,
                            anchor=tk.NW,
                            fill=tk.X)

        img_size = tuple([self.winfo_reqheight()] * 2)
        search_img = utils.get_tkimage(light_image='search-black.png',
                                       dark_image='search-white.png',
                                       size=img_size)
        self.search_label = ctk.CTkLabel(self.container,
                                         text='',
                                         image=search_img)
        self.search_label.pack(side=tk.LEFT,
                               anchor=tk.NW,
                               padx=(6, 0),
                               pady=(3, 3))

        self.search_bar = ctk.CTkEntry(self.container,
                                       placeholder_text=placeholder,
                                       border_width=0,
                                       font=fonts.BODY)
        self.search_bar.pack(side=tk.LEFT,
                             anchor=tk.NW,
                             fill=tk.BOTH,
                             expand=True,
                             padx=(0, _border_width + 3),
                             pady=(_border_width, _border_width))

    def get(self) -> str:
        return self.search_bar.get()

    def clear(self):
        self.search_bar.delete(0, ctk.END)
        self.search_bar.configure(placeholder_text=self.placeholder)
