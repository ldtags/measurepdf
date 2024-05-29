import re

from src.exceptions import UnauthorizedError
from src.app.models import Model
from src.app.views import View


def __validate_token_input_char(_input: str | None=None) -> bool:
    if _input is None or _input == '':
        return True

    if not re.fullmatch('^[a-zA-Z0-9 ]$', _input):
        return False

    return True


class AuthController:
    def __init__(self, model: Model, view: View):
        self.model = model
        self.view = view
        self.page = view.auth
        self.__bind()

    def show(self):
        self.page.tkraise()

    def __bind(self):
        self.page.auth_btn.configure(command=self.authorize)
        self.page.bind('<Button-1>', lambda _: self.page.focus_set())
        self.page.container.bind('<Button-1>', lambda _: self.page.focus_set())
        self.page.auth_label.bind('<Button-1>', lambda _: self.page.auth_label.focus_set())
        self.page.auth_btn.bind('<Button-1>', lambda _: self.page.auth_btn.focus_set())
        self.page.err_label.bind('<Button-1>', lambda _: self.page.err_label.focus_set())

    def authorize(self):
        token_header = 'Token'
        token = self.page.auth_input.get()
        if token == '':
            self.page.display_err('Please enter an auth token...')
            return
            
        if ' ' in token:
            split_token = token.split(' ')
            if len(split_token) > 2:
                self.page.display_err(f'Invalid auth token format: {token}')
                return

            if split_token[0].lower() != token_header.lower():
                self.page.display_err(f'Invalid token header: {split_token[0]}')
                return

            token = split_token[1]

        if not re.fullmatch('^[a-zA-Z0-9]+$', token):
            self.page.display_err(f'Invalid auth token: {token}')
            return

        self.model.connect(f'{token_header} {token}')
        try:
            measure_ids, count = self.model.connection.get_init_measure_ids()
            self.model.home.measure_ids = measure_ids
            self.model.home.count = count
            self.view.home.measure_id_list.measure_ids = measure_ids
            self.view.show('home')
        except UnauthorizedError:
            self.page.display_err('Unauthorized token')
