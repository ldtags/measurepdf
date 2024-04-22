import os
import tkinter as tk


_PATH = os.path.abspath(os.path.dirname(__file__))


def get_path(file_name: str) -> str:
    file_path = os.path.join(_PATH, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'no asset named {file_name} exists')
    return file_path


def get_tkimage(file_name: str) -> tk.PhotoImage:
    file_path = get_path(file_name)
    return tk.PhotoImage(file=file_path)
