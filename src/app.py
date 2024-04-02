import re
import customtkinter as ctk
from customtkinter import (
    TOP,
    BOTH,
    NSEW,
    CENTER
)
from typing import Type


RE_AUTH_TOKEN = re.compile('^[a-zA-Z0-9]+$')


ctk.set_appearance_mode('system')
ctk.set_default_color_theme('dark-blue')


class App(ctk.CTk):
    def __init__(self, width = 1100, height = 580):
        super().__init__()

        self.auth_token = ctk.StringVar(master=self, name='auth_token')

        self.title('  eTRM Measure(s) to PDF')
        self.geometry(f'{width}x{height}')

        container = ctk.CTkFrame(self)
        container.pack(side=TOP, fill=BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames: dict[Type[ctk.CTkFrame], ctk.CTkFrame] = {}

        for f_class in (AuthFrame, MainFrame):
            frame = f_class(container, self)
            self.frames[f_class] = frame
            frame.grid(row=0, column=0, sticky=NSEW)

        self._show_frame(AuthFrame)

    def _show_frame(self, f_class: Type[ctk.CTkFrame]):
        frame = self.frames[f_class]
        frame.tkraise()

    def _set_auth_token(self, token: str):
        self.auth_token = token

    def run(self):
        self.mainloop()


class AuthFrame(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: App, **kwargs):
        super().__init__(parent, **kwargs)

        self.controller = controller

        container = ctk.CTkFrame(self)
        container.pack(anchor=CENTER, expand=True)
        container.grid_rowconfigure((0, 3), weight=1)
        container.grid_rowconfigure((1, 2), weight=0)
        container.grid_columnconfigure(0, weight=1)

        auth_label = ctk.CTkLabel(container,
                                  text='eTRM Authorization Token:')

        auth_input = ctk.CTkEntry(container,
                                  width=200,
                                  placeholder_text='Token 12345b73a0b63...')

        err_label = ctk.CTkLabel(container,
                                 width=200,
                                 wraplength=200,
                                 text='',
                                 text_color='red')

        auth_btn = ctk.CTkButton(container,
                                 text='Continue',
                                 command=self._auth_btn_onclick)

        self.auth_input = auth_input
        self.err_label = err_label

        self.bind('<Button-1>', lambda _: self.focus_set())
        container.bind('<Button-1>', lambda _: self.focus_set())
        auth_label.bind('<Button-1>', lambda _: auth_label.focus_set())
        auth_btn.bind('<Button-1>', lambda _: auth_btn.focus_set())

        auth_label.grid(row=0, column=0, sticky='s', pady=(10, 2), padx=(15, 15))
        auth_input.grid(row=1, column=0, pady=(2, 2), padx=(15, 15))
        auth_btn.grid(row=3, column=0, sticky='n', pady=(10, 13), padx=(15, 15))

    def _display_err(self, err_msg: str):
        self.err_label.grid(row=2, column=0, pady=(2, 2), padx=(15, 15))
        self.err_label.configure(text=err_msg)

    def _auth_btn_onclick(self):
        token_header = 'Token'
        token = self.auth_input.get()
        if token == '':
            self._display_err('Please enter an auth token...')
            return
            
        if ' ' in token:
            split_token = token.split(' ')
            if len(split_token) > 2:
                self._display_err(f'Invalid auth token format: {token}')
                return

            if split_token[0] != token_header:
                self._display_err(f'Invalid token header: {split_token[0]}')
                return

            token = split_token[1]

        if not re.fullmatch(RE_AUTH_TOKEN, token):
            self._display_err(f'Invalid auth token: {token}')
            return

        self.controller.setvar('auth_token', f'{token_header} {token}')
        self.controller._show_frame(MainFrame)


class MainFrame(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: App, **kwargs):
        super().__init__(parent, **kwargs)

        
