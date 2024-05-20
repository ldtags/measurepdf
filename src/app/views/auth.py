import webbrowser
import customtkinter as ctk

import src.app.styles as styles


def open_url(url: str):
    webbrowser.open(url)


class HelpWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTkFrame, **kwargs):
        self.parent = parent

        super().__init__(parent, **kwargs)
        self.deiconify()
        self.title(' Help')
        self.resizable(width=False, height=False)

        self.grid_columnconfigure((0), weight=0)
        self.grid_columnconfigure((1), weight=1)

        line_spacing = (5, 5)
        y_margin = (15, 15)
        x_margin = (15, 15)

        intro_text = 'Generating an eTRM API Key:'
        self.intro_label = ctk.CTkLabel(self,
                                        text=intro_text,
                                        font=styles.FXD_FONT_HEADER)
        self.intro_label.grid(row=0,
                              column=0,
                              columnspan=2,
                              sticky=ctk.W,
                              pady=(y_margin[0], line_spacing[1]),
                              padx=x_margin)

        item1_text = '1) Navigate to '
        self.item1_label = ctk.CTkLabel(self,
                                        text=item1_text,
                                        font=styles.FXD_FONT)
        self.item1_label.grid(row=1,
                              column=0,
                              sticky=ctk.W,
                              pady=line_spacing,
                              padx=(x_margin[0], 0))

        item1_link_text = 'caetrm.com/dashboard/#user'
        self.item1_link = ctk.CTkLabel(self,
                                       text=item1_link_text,
                                       font=styles.FXD_FONT,
                                       text_color='#9eb273',
                                       cursor='hand2')
        self.item1_link.grid(row=1,
                             column=1,
                             sticky=ctk.W,
                             pady=line_spacing,
                             padx=(0, x_margin[1]))
        self.item1_link.bind('<Button-1>',
                             lambda e: open_url('caetrm.com/dashboard/#user'))
        
        item2_text = '2) Open the profile menu by selecting the avatar icon'
        self.item2_label = ctk.CTkLabel(self,
                                        text=item2_text,
                                        font=styles.FXD_FONT)
        self.item2_label.grid(row=2,
                              column=0,
                              columnspan=2,
                              sticky=ctk.W,
                              pady=line_spacing,
                              padx=x_margin)

        item3_text = ('3) Open the user detail menu by selecting the'
                      ' PROFILE option')
        self.item3_label = ctk.CTkLabel(self,
                                        text=item3_text,
                                        font=styles.FXD_FONT)
        self.item3_label.grid(row=3,
                              column=0,
                              columnspan=2,
                              sticky=ctk.W,
                              pady=line_spacing,
                              padx=x_margin)

        item4_text = ('4) Select the EDIT option on the top right of the'
                      ' user detail menu to open the edit user menu')
        self.item4_label = ctk.CTkLabel(self,
                                        text=item4_text,
                                        font=styles.FXD_FONT)
        self.item4_label.grid(row=4,
                              column=0,
                              columnspan=2,
                              sticky=ctk.W,
                              pady=line_spacing,
                              padx=x_margin)
    
        item5_text = ('5) Select the API option on the left-hand navbar'
                      ' of the edit user menu')
        self.item5_label = ctk.CTkLabel(self,
                                        text=item5_text,
                                        font=styles.FXD_FONT)
        self.item5_label.grid(row=5,
                              column=0,
                              columnspan=2,
                              sticky=ctk.W,
                              pady=line_spacing,
                              padx=x_margin)

        item6_text = ('6) Generate your API key by selecting the'
                     ' \"Generate key\" button')
        self.item6_label = ctk.CTkLabel(self,
                                        text=item6_text,
                                        font=styles.FXD_FONT)
        self.item6_label.grid(row=6,
                              column=0,
                              columnspan=2,
                              sticky=ctk.W,
                              pady=(line_spacing[0], y_margin[1]),
                              padx=x_margin)

        x = parent.winfo_x() + parent.winfo_width() // 2
        y = parent.winfo_y() + parent.winfo_height() // 2
        self.geometry(f'+{x}+{y}')
        self.lift()

        if self.winfo_exists():
            self.grab_set()

    def wait(self):
        if self.winfo_exists():
            self.parent.wait_window(self)
            self.grab_release()


class AuthPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, **kwargs):
        super().__init__(parent, **kwargs)

        self.parent = parent

        self.grid(row=0, column=0, sticky=ctk.NSEW)
        self.grid_rowconfigure((0, 2), weight=1)
        self.grid_rowconfigure((1), weight=0)
        self.grid_columnconfigure((0, 2), weight=1)
        self.grid_columnconfigure((1), weight=0)

        self.help_prompt: HelpWindow | None = None

        self.container = ctk.CTkFrame(self)
        self.container.grid(row=1,
                            column=1,
                            sticky=ctk.NSEW)
        self.container.grid_rowconfigure((0, 3), weight=1)
        self.container.grid_rowconfigure((1, 2), weight=0)
        self.container.grid_columnconfigure((0, 1), weight=1)

        self.auth_label = ctk.CTkLabel(self.container,
                                       text='eTRM API Key:')
        self.auth_label.grid(row=0,
                             column=0,
                             columnspan=2,
                             sticky=ctk.S,
                             pady=(10, 2),
                             padx=(15, 15))

        self.auth_input = ctk.CTkEntry(self.container,
                                       width=200,
                                       placeholder_text='Token 12c45b73a0b...')
        self.auth_input.grid(row=1,
                             column=0,
                             columnspan=2,
                             pady=(2, 2),
                             padx=(15, 15))

        self.help_btn = ctk.CTkButton(self.container,
                                      text='Help',
                                      command=self.open_help)
        self.help_btn.grid(row=3,
                           column=0,
                           sticky=ctk.N,
                           pady=(10, 13),
                           padx=(15, 7.5))

        self.auth_btn = ctk.CTkButton(self.container,
                                      text='Continue')
        self.auth_btn.grid(row=3,
                           column=1,
                           sticky=ctk.N,
                           pady=(10, 13),
                           padx=(7.5, 15))

        self.err_label = ctk.CTkLabel(self,
                                      width=200,
                                      wraplength=200,
                                      text='',
                                      text_color='red')
        self.err_label.grid(row=2,
                            column=0,
                            columnspan=2,
                            sticky=ctk.N,
                            pady=(2, 2),
                            padx=(15, 15))

    def display_success(self):
        self.err_label.configure(text='Success! Feching measures...',
                                 text_color='green')

    def display_err(self, err_msg: str):
        self.err_label.configure(text=err_msg,
                                 text_color='red')

    def open_help(self):
        if self.help_prompt is None or not self.help_prompt.winfo_exists():
            self.help_prompt = HelpWindow(self)
        self.help_prompt.wm_transient(self.parent)
        self.help_prompt.focus()
        self.help_prompt.wait()
        self.help_prompt = None
