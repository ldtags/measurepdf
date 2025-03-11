from reportlab.lib import colors


def rgb_color(red: float, green: float, blue: float) -> colors.Color:
    return colors.Color(red=(red/255), green=(green/255), blue=(blue/255))


COLORS = {
    "TableHeaderLight": rgb_color(174, 141, 100),
    "TableHeaderDark": rgb_color(153, 121, 80),
    "TableRowLight": rgb_color(242, 242, 242),
    "TableRowAltLight": rgb_color(230, 230, 230),
    "TableRowDark": rgb_color(230, 230, 230),
    "TableRowAltDark": rgb_color(217, 217, 217),
    "ReferenceTagBG": rgb_color(100, 162, 68),
    "LightBrown": rgb_color(173, 140, 99),
    "DarkBrown": rgb_color(153, 121, 80),
    "Green": rgb_color(100, 163, 69),
    "RevisionLogGridLine": rgb_color(198, 175, 147),
    "RevisionLogHeaderBG": rgb_color(241, 234, 227),
    "h1": rgb_color(140, 110, 74),
    "LightBlack": rgb_color(64, 64, 64),
    "UseCategoryRowBG": rgb_color(232, 232, 232),
    "ResGreen": rgb_color(181, 230, 162),
    "MFCRed": rgb_color(251, 226, 213),
    "NRBlue": rgb_color(192, 230, 245)
}
