import src.resources as resources
from src.app import Controller


def app_controller(mode: str) -> Controller:
    controller = Controller()
    if mode == "dev":
        api_key = resources.get_api_key("admin")
        controller.connect(api_key)

    return controller


def start_app(run_mode: str) -> None:
    controller = app_controller(run_mode)
    controller.start()    
