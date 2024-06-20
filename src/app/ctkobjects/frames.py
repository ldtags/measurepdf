import tkinter as tk
import customtkinter as ctk


class Frame(ctk.CTkFrame):
    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, **kwargs)

        self.parent = parent
