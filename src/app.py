import tkinter as tk
import customtkinter as ctk
from typing import Type

class AuthFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)


class MainFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        ctk.CTkFrame.__init__(self, parent)


class App(ctk.CTk):
    def __init__(self, height = 580, width = 1100, **kwargs):
        ctk.CTk.__init__(self, **kwargs) 

        self._set_appearance_mode('dark')
        self.title('  eTRM Measure(s) to PDF')
        self.geometry(f'{width}x{height}')

        container = ctk.CTkFrame(self)
        container.pack(side = 'top', fill = 'both', expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.frames: dict[Type[ctk.CTkFrame], ctk.CTkFrame] = {}

        for F in (AuthFrame, MainFrame):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky='NSEW')

        self._show_frame(AuthFrame)

    def _show_frame(self, F: Type[ctk.CTkFrame]):
        frame = self.frames[F]
        frame.tkraise()

    def run(self):
        self.mainloop()
