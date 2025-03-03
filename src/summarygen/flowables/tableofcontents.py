from ast import literal_eval
from typing import Any, Literal
from reportlab.lib.units import cm, inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    IndexingFlowable,
    Paragraph,
    Spacer,
    Table
)

from src.summarygen.styles import (
    ParagraphStyle,
    TableStyle,
    get_toc_style,
    DEF_PSTYLE
)


delta = 1 * cm
epsilon = 0.5 * cm

DEFAULT_LEVEL_STYLES = [DEF_PSTYLE.bold, DEF_PSTYLE]


def add_toc_links(
    canvas: Canvas,
    pages: list[tuple[int, str]],
    avail_width: float,
    avail_height: float,
) -> None:
    for _, key in pages:
        if not key:
            continue

        canvas.linkRect("", key, (0, 0, avail_width, avail_height), relative=1)


class TOCEntry:
    def __init__(
        self,
        text: str,
        page_num: int,
        type: Literal["measure", "use_category", "generic"] = "generic",
        active_life: str | None = None,
        measure_name: str | None = None,
        key: str | None = None
    ) -> None:
        self.text = text
        self.page_num = page_num
        self.type = type
        self.active_life = active_life
        self.measure_name = measure_name
        self.key = key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TOCEntry):
            return False

        if self.text != other.text:
            return False

        if self.page_num != other.page_num:
            return False

        if self.type != other.type:
            return False

        if self.key != other.key:
            return False

        return True


class TableOfContents(IndexingFlowable):
    def __init__(
        self,
        level_styles: list[ParagraphStyle] = DEFAULT_LEVEL_STYLES,
        table_style: TableStyle | None = None,
        dots_min_level: int = 1
    ) -> None:
        self.level_styles = level_styles
        self.table_style = table_style
        self.dots_min_level = dots_min_level
        self._table: Table | None = None
        self._entries: list[TOCEntry] = []
        self._last_entries: list[TOCEntry] = []

    def beforeBuild(self) -> None:
        # keep track of the last run
        self._last_entries = self._entries[:]
        self.clear_entries()

    def isIndexing(self) -> int:
        return 1

    def isSatisfied(self) -> bool:
        return (self._entries == self._last_entries)

    def notify(self, kind: str, stuff: tuple) -> None:
        if kind == "TOCEntry":
            self.add_entry(
                TOCEntry(
                    text=stuff[0],
                    page_num=stuff[1],
                    type="generic",
                    key=stuff[2] if len(stuff) > 2 else None
                )
            )
            return

        if kind == "TOCEntryUC":
            self.add_entry(
                TOCEntry(
                    text=stuff[0],
                    page_num=stuff[1],
                    type="use_category",
                    key=stuff[2] if len(stuff) > 2 else None
                )
            )
            return

        if kind == "TOCEntryM":
            self.add_entry(
                TOCEntry(
                    text=stuff[0],
                    page_num=stuff[1],
                    type="measure",
                    measure_name=stuff[2],
                    active_life=stuff[3],
                    key=stuff[4] if len(stuff) > 4 else None
                )
            )
            return

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        """Wraps the table of contents on `avail_width` and `avail_height`.

        All table properties should be known by the time this method is called.
        """

        # makes an internal table which does all the work.
        # we draw the last run's entries!
        # if there are none, we make some dummy data to keep the table from complaining.
        if self._last_entries == []:
            _temp_entries = [
                TOCEntry(
                    text="Placeholder for table of contents",
                    page_num=0,
                    type="use_category"
                )
            ]
        else:
            _temp_entries = self._last_entries

        def draw_toc_entry_end(canvas: Canvas, kind, label: str) -> None:
            label_parts = label.split(",")
            page = int(label_parts[0])
            key = literal_eval(label_parts[2])
            add_toc_links(canvas, [(page, key)], avail_width, avail_height)

        self.canv.draw_toc_entry_end = draw_toc_entry_end

        table_data = []
        uc_row_indices: list[int] = []
        generic_indices: list[int] = []
        for y, entry in enumerate(_temp_entries):
            level = 0 if entry.type == "use_category" else 1
            style = self.get_level_style(level)
            key = entry.key
            text = entry.text
            if key is not None:
                text = f"<a href=\"{key}\">{text}</a>"
                key_val = repr(key).replace(",", "\\x2c").replace("\"", "\\x2c")
            else:
                key_val = None

            row = [Paragraph(text, style=style)]
            match entry.type:
                case "use_category":
                    row.extend([""] * 3)
                    uc_row_indices.append(y)
                case "generic":
                    row.insert(0, "")
                    row.extend([""] * 2)
                    generic_indices.append(y)
                case "measure":
                    row.insert(0, "")
                    row.append(Paragraph(entry.measure_name, style=style))
                    row.append(Paragraph(entry.active_life, style=style))
                case other:
                    raise ValueError(f"Invalid TOC entry type: {other}")

            f_name = "draw_toc_entry_end"
            f_kwargs: dict[str, Any] = {
                "label": (entry.page_num, level, key_val)
            }
            kw_text = ""
            for kw, arg in f_kwargs.items():
                if isinstance(arg, tuple):
                    kw_str = ",".join([str(arg_item) for arg_item in arg])
                else:
                    kw_str = str(arg)

                kw_text += f" {kw}=\"{kw_str}\""

            row.append(
                Paragraph(
                    f"{entry.page_num}<onDraw name=\"{f_name}\" {kw_text}/>",
                    style=style
                )
            )
            table_data.append(row)

        table_style = self.table_style or get_toc_style(uc_row_indices, generic_indices)
        col_widths = [
            avail_width * 0.03,
            avail_width * 0.2,
            avail_width * 0.37,
            avail_width * 0.3,
            avail_width * 0.1
        ]
        self._table = Table(table_data, colWidths=col_widths, style=table_style)
        self.width, self.height = self._table.wrapOn(self.canv, avail_width, avail_height)
        return (self.width, self.height)

    def split(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        """At this stage, we do not care about splitting the entries, we will
        just return a list of platypus tables.

        Presumably, the calling app has a pointer to the original
        `TableOfContents` object; platypus just sees tables.
        """

        return self._table.splitOn(self.canv, avail_width, avail_height)

    def drawOn(self, canvas: Canvas, x: int, y: int, _sW=0) -> None:
        """Don't do this at home!

        The standard calls for implementing draw(); we are hooking this in
        order to delegate ALL the drawing work to the embedded table object.
        """

        self._table.drawOn(canvas, x, y, _sW)

    def get_level_style(self, level: int) -> ParagraphStyle:
        try:
            self.level_styles[level]
        except IndexError:
            prev_style = self.get_level_style(level - 1)
            self.level_styles.append(
                ParagraphStyle(
                    name=f"{prev_style.name}-{level}-indented",
                    parent=prev_style,
                    firstLineIndent = prev_style["firstLineIndent"],
                    left_indent=prev_style["leftIndent"]
                )
            )

        return self.level_styles[level]

    def add_entry(self, entry: TOCEntry) -> None:
        """Adds one entry to the table of contents.

        This allows incremental buildup by a doctemplate.

        Requires that enough styles are defined (i.e., a style for `level`).
        """

        self._entries.append(entry)

    def add_entries(self, entries: list[TOCEntry]) -> None:
        for entry in entries:
            self.add_entry(entry)

    def clear_entries(self) -> None:
        self._entries = []
