import customtkinter as ctk

from .root import Root
from .auth import AuthPage
from .home import HomePage


class View:
    def __init__(self):
        self.root = Root()
        self.auth = AuthPage(self.root.container)
        self.home = HomePage(self.root.container)
        self.pages: dict[str, ctk.CTkFrame] = {
            'auth': self.auth,
            'home': self.home
        }

    def show(self, page_name: str):
        self.pages[page_name].tkraise()

    def start(self):
        self.root.mainloop()
