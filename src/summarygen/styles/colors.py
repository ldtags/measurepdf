from reportlab.lib import colors


def rgb_color(red: float, green: float, blue: float) -> colors.Color:
    return colors.Color(red=(red/255), green=(green/255), blue=(blue/255))


COLORS = {
    'ValueTableHeaderLight': rgb_color(174, 141, 100),
    'ValueTableHeaderDark': rgb_color(153, 121, 80),
    'ValueTableRowLight': rgb_color(242, 242, 242),
    'ValueTableRowAltLight': rgb_color(230, 230, 230),
    'ValueTableRowDark': rgb_color(230, 230, 230),
    'ValueTableRowAltDark': rgb_color(217, 217, 217),
    'ReferenceTagBG': rgb_color(100, 162, 68),
    'LightBrown': rgb_color(173, 140, 99),
    'DarkBrown': rgb_color(153, 121, 80),
    'Green': rgb_color(100, 163, 69)
}
