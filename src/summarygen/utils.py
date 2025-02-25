import os
import shutil
import requests
from reportlab.platypus import Image

from src import TMP_DIR
from src.summarygen.exceptions import SummaryGenError


def download_image(url: str) -> str:
    """Downloads the image at `url` and stores it in the temp directory.

    Images downloaded this way will be removed once the running process
    terminates.

    Returns an absolute path to the downloaded image.
    """

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise SummaryGenError(f"Could not download image at {url}")

    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)

    img_name = url[url.rindex("/") + 1:]
    img_path = f"{TMP_DIR}/{img_name}"
    with open(img_path,  "wb+") as fp:
        shutil.copyfileobj(response.raw, fp)

    return img_path


def get_image(
    img_path: str,
    max_width: float | None = None,
    max_height: float | None = None,
    **kwargs
) -> Image:
    img = Image(img_path, **kwargs)
    img_width = img.imageWidth
    img_height = img.imageHeight

    if max_width is not None:
        assert max_width > 0
        scalar = img_width / (max_width - 1)
        if scalar > 1:
            img_width /= scalar
            img_height /= scalar
            img = Image(
                img_path,
                width=img_width,
                height=img_height,
                **kwargs
            )

    if max_height is not None:
        assert max_height > 0
        scalar = img_height / (max_height - 1)
        if scalar > 1:
            img_height /= scalar
            img_width /= scalar
            img = Image(
                img_path,
                width=img_width,
                height=img_height,
                **kwargs
            )

    return img


