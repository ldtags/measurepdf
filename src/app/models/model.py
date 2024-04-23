from src.etrm import ETRMConnection
from src.app.models.auth import AuthModel
from src.app.models.home import HomeModel


class Model:
    def __init__(self):
        self.connection: ETRMConnection | None = None
        self.auth = AuthModel()
        self.home = HomeModel()

    def connect(self, auth_token: str):
        self.connection = ETRMConnection(auth_token)
        self.auth.set_token(auth_token)
