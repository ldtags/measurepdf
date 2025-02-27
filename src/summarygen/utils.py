import os
import math
import shutil
import requests
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Image,
    Flowable,
    Spacer,
    Table,
    Paragraph
)

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
    img_width = img.drawWidth
    img_height = img.drawHeight

    if max_width is not None and img_width > max_width:
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

    if max_height is not None and img_height > max_height:
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


def get_flowable_width(flowable: Flowable) -> float:
    if isinstance(flowable, Table):
        try:
            width = math.fsum(flowable._argW)
        except AttributeError as err:
            raise SummaryGenError("Table does not have a width argument") from err

        return width

    if isinstance(flowable, Paragraph):
        text = ""
        try:
            for frag in flowable.frags:
                text += frag.text
        except AttributeError:
            text = flowable.text

        return stringWidth(
            text,
            flowable.style.fontName,
            flowable.style.fontSize,
            flowable.encoding
        )

    if isinstance(flowable, Spacer):
        return flowable.width

    raise SummaryGenError(f"Unsupported flowable type: {type(flowable)}")


def get_flowable_height(flowable: Flowable) -> float:
    if isinstance(flowable, Table):
        try:
            height = math.fsum(flowable._argH)
        except AttributeError as err:
            raise SummaryGenError("Table does not have a height argument") from err

        return height

    if isinstance(flowable, Paragraph):
        return flowable.style.leading

    if isinstance(flowable, Spacer):
        return flowable.height

    raise SummaryGenError(f"Unsupported flowable type: {type(flowable)}")
