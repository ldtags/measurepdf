import customtkinter as ctk


class AuthPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid(row=0, column=0, sticky=ctk.NSEW)
        self.grid_rowconfigure((0, 2), weight=1)
        self.grid_rowconfigure((1), weight=0)
        self.grid_columnconfigure((0, 2), weight=1)
        self.grid_columnconfigure((1), weight=0)

        self.container = ctk.CTkFrame(self)
        self.container.grid(row=1,
                            column=1,
                            sticky=ctk.NSEW)
        self.container.grid_rowconfigure((0, 3), weight=1)
        self.container.grid_rowconfigure((1, 2), weight=0)
        self.container.grid_columnconfigure(0, weight=1)

        self.auth_label = ctk.CTkLabel(self.container,
                                       text='eTRM Authorization Token:')
        self.auth_label.grid(row=0,
                             column=0,
                             sticky=ctk.S,
                             pady=(10, 2),
                             padx=(15, 15))

        self.auth_input = ctk.CTkEntry(self.container,
                                       width=200,
                                       placeholder_text='Token 12c45b73a0b...')
        self.auth_input.grid(row=1,
                             column=0,
                             pady=(2, 2),
                             padx=(15, 15))

        self.auth_btn = ctk.CTkButton(self.container,
                                      text='Continue')
        self.auth_btn.grid(row=3,
                           column=0,
                           sticky=ctk.N,
                           pady=(10, 13),
                           padx=(15, 15))

        self.err_label = ctk.CTkLabel(self,
                                      width=200,
                                      wraplength=200,
                                      text='',
                                      text_color='red')
        self.err_label.grid(row=2,
                            column=1,
                            sticky=ctk.N,
                            pady=(2, 2),
                            padx=(15, 15))

    def display_success(self):
        self.err_label.configure(text='Success! Feching measures...',
                                 text_color='green')

    def display_err(self, err_msg: str):
        self.err_label.configure(text=err_msg,
                                 text_color='red')
