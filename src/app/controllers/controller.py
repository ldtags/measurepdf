from src.app.models import Model
from src.app.views import View
from src.app.controllers.auth import AuthController
from src.app.controllers.home import HomeController


class Controller:
    def __init__(self):
        self.model = Model()
        self.view = View()
        self.auth = AuthController(self.model, self.view)
        self.home = HomeController(self.model, self.view)

    def connect(self, auth_token: str):
        self.model.connect(auth_token)

    def start(self):
        if self.model.connection != None:
            self.home.show()
        else:
            self.auth.show()
        self.view.start()
