import os
import customtkinter as ctk
from PIL import Image


_PATH = os.path.abspath(os.path.dirname(__file__))


def get_path(dir_name: str, file_name: str) -> str:
    file_path = os.path.join(_PATH, dir_name, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'no asset named {file_name} exists')
    return file_path


def get_tkimage(file_name: str, size: tuple[int, int] | None=None) -> ctk.CTkImage:
    file_path = get_path('images', file_name)
    return ctk.CTkImage(Image.open(file_path), size=size)
