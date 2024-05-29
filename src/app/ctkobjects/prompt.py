import customtkinter as ctk
from typing import Callable

from src import utils


class PromptWindow(ctk.CTkToplevel):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 text: str,
                 title: str=' Processing',
                 *args,
                 **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.deiconify()
        self.title(title)
        self.resizable(width=False, height=False)

        self.label = ctk.CTkLabel(self, text=text)
        self.label.pack(padx=20,
                        pady=20)

        x_offset = parent.winfo_width() // 2 - self.winfo_width() // 2
        y_offset = parent.winfo_height() // 2 - self.winfo_height() // 2
        x = parent.winfo_x() + x_offset
        y = parent.winfo_y() + y_offset
        self.geometry(f'+{x}+{y}')
        self.lift()

        if self.winfo_exists():
            self.grab_set()

    def run(self, func: Callable[..., None], *args):
        func(*args)
        self.grab_release()
        self.destroy()


class InfoPromptWindow(ctk.CTkToplevel):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 text: str,
                 title: str='',
                 *args,
                 ok_text: str='Ok',
                 **kwargs):
        self.parent = parent

        super().__init__(parent, *args, **kwargs)
        self.deiconify()
        self.title(title)
        self.resizable(width=False, height=False)
        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.label = ctk.CTkLabel(self, text=text)
        self.label.grid(row=0,
                        column=0,
                        columnspan=3,
                        sticky=ctk.NSEW,
                        padx=(10, 10),
                        pady=(10, 10))

        self.ok_btn = ctk.CTkButton(self,
                                    text=ok_text,
                                    command=self.destroy)
        self.ok_btn.grid(row=1,
                         column=1,
                         sticky=ctk.NSEW,
                         padx=(10, 10),
                         pady=(10, 10))

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


class InputPromptWindow(ctk.CTkToplevel):
    def __init__(self,
                 parent: ctk.CTkFrame,
                 text: str,
                 title: str='',
                 *args,
                 ok_text: str='Ok',
                 cancel_text: str='Cancel',
                 **kwargs):
        self.parent = parent
        self.result = False

        super().__init__(parent, *args, **kwargs)
        self.deiconify()
        self.title(title)
        self.resizable(width=False, height=False)
        self.width = 400
        for word in text.split(' '):
            word_len = len(word) * 7.5
            if word_len > self.width:
                self.width = word_len
        self.height = (len(text) / 100) * 200
        self.geometry(f'{self.width}x{self.height}')
        self.grid_rowconfigure((0), weight=1)
        self.grid_rowconfigure((1), weight=0)
        self.grid_columnconfigure((0, 3), weight=0)
        self.grid_columnconfigure((1, 2), weight=1)

        self.label = ctk.CTkLabel(self,
                                  text=text,
                                  wraplength=self.width - 20)
        self.label.grid(row=0,
                        column=1,
                        columnspan=2,
                        sticky=ctk.NSEW,
                        padx=(10, 10),
                        pady=(10, 10))

        self.ok_btn = ctk.CTkButton(self,
                                    text=ok_text,
                                    command=self.ok_cmd)
        self.ok_btn.grid(row=1,
                         column=2,
                         columnspan=2,
                         sticky=ctk.NSEW,
                         padx=(10, 10),
                         pady=(10, 10))

        self.cancel_btn = ctk.CTkButton(self,
                                        text=cancel_text,
                                        fg_color='#FF0000',
                                        hover_color='#D50000',
                                        cursor='hand2',
                                        command=self.cancel_cmd)
        self.cancel_btn.grid(row=1,
                             column=0,
                             columnspan=2,
                             sticky=ctk.NSEW,
                             padx=(10, 10),
                             pady=(10, 10))

        x = parent.winfo_x() + parent.winfo_width() // 2 - self.winfo_width() // 2
        y = parent.winfo_y() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f'+{x}+{y}')
        self.lift()

        if self.winfo_exists():
            self.grab_set()

    def get_result(self):
        if self.winfo_exists():
            self.parent.wait_window(self)
        return self.result

    def ok_cmd(self):
        self.result = True
        self.grab_release()
        self.destroy()

    def cancel_cmd(self):
        self.result = False
        self.grab_release()
        self.destroy()


class FileDialogueWindow(ctk.CTkToplevel):
    def __init__(self,
             parent: ctk.CTkFrame,
             default_dest: str,
             default_fname: str,
             title: str='',
             *args,
             ok_text: str='Ok',
             cancel_text: str='Cancel',
             **kwargs):
        self.parent = parent
        self.result: tuple[str, str, bool] = ('', '', False)

        super().__init__(parent, *args, **kwargs)
        self.deiconify()
        self.title(title)
        self.resizable(width=False, height=False)
        self.geometry(f'600x200')
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.grid_columnconfigure((0, 3), weight=0)
        self.grid_columnconfigure((1, 2), weight=1)

        self.folder_label = ctk.CTkLabel(self,
                                         text='Destination Folder:')
        self.folder_label.grid(row=0,
                               column=0,
                               sticky=ctk.E,
                               padx=(20, 10),
                               pady=(10, 10))

        self.dir_path = ctk.StringVar(self, default_dest, 'dir_path')
        self.folder_entry = ctk.CTkEntry(self,
                                         textvariable=self.dir_path)
        self.folder_entry.grid(row=0,
                               column=1,
                               columnspan=2,
                               sticky=ctk.NSEW,
                               padx=(10, 10),
                               pady=(20, 20))

        self.dir_btn = ctk.CTkButton(self,
                                     text='',
                                     image=utils.get_tkimage(
                                        'folder.png',
                                        size=(24, 24)),
                                     width=24,
                                     height=24,
                                     command=self.open_fd)
        self.dir_btn.grid(row=0,
                          column=3,
                          sticky=ctk.NSEW,
                          padx=(5, 20),
                          pady=(20, 20))

        self.file_label = ctk.CTkLabel(self,
                                       text='File Name:')
        self.file_label.grid(row=1,
                             column=0,
                             sticky=ctk.E,
                             padx=(20, 10),
                             pady=(10, 10))

        self.file_name = ctk.StringVar(self, default_fname, 'file_name')
        self.file_entry = ctk.CTkEntry(self,
                                       textvariable=self.file_name)
        self.file_entry.grid(row=1,
                             column=1,
                             columnspan=2,
                             sticky=ctk.NSEW,
                             padx=(10, 5),
                             pady=(15, 15))
        
        self.pdf_label = ctk.CTkLabel(self,
                                      text='.pdf')
        self.pdf_label.grid(row=1,
                            column=3,
                            sticky=ctk.W,
                            padx=(5, 20),
                            pady=(15, 15))
        
        self.ok_btn = ctk.CTkButton(self,
                                    text=ok_text,
                                    command=self.ok_cmd)
        self.ok_btn.grid(row=2,
                         column=2,
                         columnspan=2,
                         sticky=ctk.NSEW,
                         padx=(30, 30),
                         pady=(15, 15))

        self.cancel_btn = ctk.CTkButton(self,
                                        text=cancel_text,
                                        fg_color='#FF0000',
                                        hover_color='#D50000',
                                        cursor='hand2',
                                        command=self.cancel_cmd)
        self.cancel_btn.grid(row=2,
                             column=0,
                             columnspan=2,
                             sticky=ctk.NSEW,
                             padx=(30, 30),
                             pady=(15, 15))
        
        x = parent.winfo_x() + parent.winfo_width() // 2 - self.winfo_width()
        y = parent.winfo_y() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f'+{x}+{y}')
        self.lift()

        if self.winfo_exists():
            self.grab_set()

    def get_result(self):
        if self.winfo_exists():
            self.parent.wait_window(self)
        return self.result

    def open_fd(self):
        dir_path = ctk.filedialog.askdirectory(initialdir=self.dir_path.get(),
                                               mustexist=True)
        if dir_path != '':
            self.dir_path.set(dir_path)

    def ok_cmd(self):
        self.result = (self.dir_path.get(),
                       self.file_name.get(),
                       True)
        self.grab_release()
        self.destroy()

    def cancel_cmd(self):
        self.result = ('', '', False)
        self.grab_release()
        self.destroy()
