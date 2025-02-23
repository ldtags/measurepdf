from src.summarygen.models.enums import TextStyle


TAG_STYLE_MAP = {
    "em": TextStyle.Italic,
    "strong": TextStyle.Strong,
    "sup": TextStyle.Superscript,
    "sub": TextStyle.Subscript,
    "pre": TextStyle.Pre
}
