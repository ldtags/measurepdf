class AuthModel:
    def __init__(self):
        self.auth_token: str | None = None

    def is_authorized(self):
        return self.auth_token != None

    def set_token(self, token: str):
        self.auth_token = token
