import os
from reportlab.platypus import Table, Paragraph
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.lib.styles import ParagraphStyle


from src import _ROOT
from src.etrm.models import Measure


class Font:
    """Registerable font for the reportlab library
    
    Fonts must be stored in the `assets` directory as a directory named
    `asset_dir` that contains all font files

    Each font file must follow the name format `name`-`style`.ttf

    Supported (and required) font styles: `Regular`, `Bold`, `Italic`,
    `BoldItalic`

    Font styles are case specific
    """

    def __init__(self, name: str, asset_dir: str):
        self.name = name
        self.path = os.path.join(_ROOT, 'assets', asset_dir)
        self.regular = TTFont(
            f'{name}',
            os.path.join(self.path, f'{name}-Regular.ttf'))

        self.bold = TTFont(
            f'{name}B',
            os.path.join(self.path, f'{name}-Bold.ttf'))

        self.italic = TTFont(
            f'{name}I',
            os.path.join(self.path, f'{name}-Italic.ttf'))

        self.bold_italic = TTFont(
            f'{name}BI',
            os.path.join(self.path, f'{name}-BoldItalic.ttf'))

    def register(self):
        pdfmetrics.registerFont(self.regular)
        pdfmetrics.registerFont(self.bold)
        pdfmetrics.registerFont(self.italic)
        pdfmetrics.registerFont(self.bold_italic)
        registerFontFamily(
            self.name,
            normal=self.name,
            bold=f'{self.name}B',
            italic=f'{self.name}I',
            boldItalic=f'{self.name}BI')


def register_fonts():
    Font('SourceSansPro', 'source-sans-pro').register()


class TableHeader(Paragraph):
    def __init__(self,
                 text: str,
                 font_name: str='SourceSansPro',
                 font_size: float=13.5,
                 bold: bool=True,
                 italic: bool=False):
        self.font_name = font_name
        self.font_size = font_size
        self.style = ParagraphStyle('Normal',
                                    fontName=self.font_name,
                                    fontSize=self.font_size)

        self.text = text
        if italic:
            self.text = f'<i>{self.text}</i>'
        if bold:
            self.text = f'<b>{self.text}</b>'

        super().__init__(self.text, self.style)


class MeasurePdf:
    def __init__(self,
                 filename: str='measure_summary',
                 pagesize: tuple[float, float]=letter):
        self.measures: list[Measure] = []
        self.filename = filename + '.pdf'
        self.canvas = Canvas(self.filename, pagesize=pagesize)
        self.width, self.height = pagesize
        register_fonts()

    def _write_measure_details_table(self, measure: Measure):
        data = [
            [TableHeader('Statewide Measure ID'), measure.statewide_measure_id],
            [TableHeader('Measure Name'), measure.name],
            [TableHeader('Effective Date'), measure.effective_start_date],
            [TableHeader('End Date'), measure.sunset_date or ''],
            [TableHeader('PA Lead'), measure.pa_lead]
        ]
        style = [
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]
        Table(data, style=style)

    def add_measure(self, measure: Measure):
        self.measures.append(measure)
        self._write_measure_details_table(measure)
        self.canvas.showPage()

    def reset(self):
        del self.canvas
        self.canvas = Canvas(self.filename)

    def build(self) -> Canvas:
        self.canvas.save()
        return self.canvas
    