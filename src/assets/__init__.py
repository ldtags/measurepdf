import os


_PATH = os.path.abspath(os.path.dirname(__file__))


def get_path(asset_path: str, exists: bool = True) -> str:
    if asset_path.startswith("assets") and len(asset_path) >= 7:
        asset_path = asset_path[6:]

    if not asset_path.startswith("/"):
        asset_path = "/" + asset_path

    file_path = os.path.normpath(_PATH + asset_path)
    if exists and not os.path.exists(file_path):
        raise FileNotFoundError(f"No asset exists at {asset_path}")

    return file_path
