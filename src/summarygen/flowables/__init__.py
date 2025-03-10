"""Module for all custom flowables.

This module contains all custom flowables that are used within the 
summary PDF generation process. When creating a new custom flowable,
add it to this module.

Extending Custom Tables:
    ReportLab uses a weird process for constructing instances of
    the Table class. From my testing and looking through the source
    code, it seems that if the Table instance was constructed with both
    strings and flowables, the constructor will be called again. This is
    referred to as the "data normalization" process and a specific keyword
    arg (normalizedData) will be passed as a signifier. This makes extending
    the Table class weird, but doable. Examples of how to accommodate this
    process can be found in the custom Table flowables below.
"""


__all__ = [
    "Spacer",
    "Reference",
    "ExcelLink",
    "NEWLINE",
    "ParagraphLine",
    "SummaryParagraph",
    "TableCell",
    "BasicTable",
    "ValueTable",
    "ValueTableHeader",
    "EmbeddedValueTable",
    "TitlePage",
    "TitleSection",
    "TitleSectionContainer",
    "TitleSectionSubContainer",
    "SunsettedMeasuresTable",
    "TableOfContents",
    "CoverPage",
    "VersionContainer",
    "split_word",
    "wrap_elements"
]


from src.summarygen.flowables.general import (
    Spacer,
    Reference,
    ExcelLink,
    NEWLINE
)
from src.summarygen.flowables.paragraph import (
    ParagraphLine,
    SummaryParagraph
)
from src.summarygen.flowables.tables import (
    TableCell,
    BasicTable,
    ValueTable,
    ValueTableHeader,
    EmbeddedValueTable,
    SunsettedMeasuresTable
)
from src.summarygen.flowables.titlepage import (
    TitlePage,
    TitleSection,
    TitleSectionContainer,
    TitleSectionSubContainer
)
from src.summarygen.flowables.coverpage import (
    CoverPage,
    VersionContainer
)
from src.summarygen.flowables.tableofcontents import (
    TableOfContents
)
from src.summarygen.flowables.utils import (
    split_word,
    wrap_elements
)
