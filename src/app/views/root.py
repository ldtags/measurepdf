import customtkinter as ctk

from src import asset_path, summarygen
from src.app import themes


ctk.set_default_color_theme('dark-blue')
ctk.set_appearance_mode('system')


class Root(ctk.CTk):
    def __init__(self, width: int=1100, height: int=580):
        super().__init__()

        self.title('Measure Summary Generator')
        self.iconbitmap(asset_path('etrm.ico', 'images'))
        self.geometry(f'{width}x{height}')
        self.minsize(width=550, height=290)

        self.protocol('WM_DELETE_WINDOW', lambda _: summarygen.clean())

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=0, sticky=ctk.NSEW)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
