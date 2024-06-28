import copy
import unittest as ut
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.summarygen.models import (
    ParagraphElement,
    ElemType,
    TextStyle
)
from src.summarygen.styling import (
    BetterParagraphStyle,
    DEF_PSTYLE,
    PSTYLES
)
from src.exceptions import (
    ElementJoinError
)


class ParagraphElementTestCase(ut.TestCase):
    def assert_element_type(self,
                            element_type: ElemType,
                            expected_type: ElemType
                           ) -> None:
        for _type in ElemType:
            if _type is expected_type:
                self.assertEqual(element_type, _type)
            else:
                self.assertNotEqual(element_type, _type)

    def assert_text_styles(self,
                           element_styles: list[TextStyle],
                           expected_styles: list[TextStyle]
                          ) -> None:
        for style in TextStyle:
            if style in expected_styles:
                self.assertIn(style, element_styles)
            else:
                self.assertNotIn(style, element_styles)

    def assert_element(self,
                       text: str,
                       expected_xml: str,
                       element_type: ElemType,
                       text_styles: list[TextStyle],
                       base_style: BetterParagraphStyle | None=None,
                       expected_style: BetterParagraphStyle=DEF_PSTYLE
                      ) -> None:
        text_copy = copy.deepcopy(text)
        type_copy = copy.deepcopy(ElemType)
        text_styles_copy = copy.deepcopy(text_styles)
        para_style_copy = copy.deepcopy(base_style)
        element = ParagraphElement(text=text,
                                   type=element_type,
                                   styles=text_styles,
                                   style=base_style)

        # test __init__ for any vars that may have been modified
        self.assertEqual(text, text_copy)
        self.assertEqual(element_type, type_copy)
        self.assertEqual(text_styles, text_styles_copy)
        self.assertEqual(base_style, para_style_copy)

        # assert correct properties
        self.assertEqual(element.__style, base_style)
        self.assertEqual(element.style, expected_style)
        self.assertEqual(element.text, text)
        self.assertEqual(element.text_xml, expected_xml)
        self.assertEqual(element.width, stringWidth(text,
                                                    expected_style.font_name,
                                                    expected_style.font_size))
        self.assertEqual(element.height, expected_style.leading)
        self.assertEqual(element.font_size, expected_style.font_size)
        self.assertEqual(element.font_name, expected_style.font_name)
        for _type in ElemType:
            if _type is element_type:
                self.assertEqual(element.type, _type)
            else:
                self.assertNotEqual(element.type, _type)
        for style in TextStyle:
            if style in text_styles:
                self.assertIn(style, element.styles)
            else:
                self.assertNotIn(style, element.styles)

    def test_normal_element(self):
        self.assert_element(text='test',
                            expected_xml='test',
                            element_type=ElemType.TEXT,
                            text_styles=[TextStyle.NORMAL])

    def test_bold_element(self):
        self.assert_element(text='test',
                            expected_xml=f'<b>test</b>',
                            element_type=ElemType.TEXT,
                            text_styles=[TextStyle.STRONG],
                            expected_style=DEF_PSTYLE.bold)

    def test_italic_element(self):
        self.assert_element(text='test',
                            expected_xml=f'<b>test</b>',
                            element_type=ElemType.TEXT,
                            text_styles=[TextStyle.ITALIC],
                            expected_style=DEF_PSTYLE.italic)

    def test_split(self):
        ...

    def test_copy(self):
        ...

    def test_join(self):
        space = ParagraphElement('', ElemType.SPACE)
        ref_tag = ParagraphElement('R100', ElemType.REF)

        normal_elem = ParagraphElement('test', styles=[TextStyle.NORMAL])
        styled_normal_elem = normal_elem.copy(style=PSTYLES['Test'])
        italic_elem = ParagraphElement('test', styles=[TextStyle.ITALIC])
        styled_italic_elem = italic_elem.copy(style=PSTYLES['Test'])
        bold_elem = ParagraphElement('test', styles=[TextStyle.STRONG])
        styled_bold_elem = bold_elem.copy(style=PSTYLES['Test'])

        with self.assertRaises(ElementJoinError):
            normal_elem.join(space)
            normal_elem.join(ref_tag)
            normal_elem.join(italic_elem)
            normal_elem.join(bold_elem)
            normal_elem.join(styled_normal_elem)

            italic_elem.join(space)
            italic_elem.join(ref_tag)
            italic_elem.join(normal_elem)
            italic_elem.join(bold_elem)
            italic_elem.join(styled_italic_elem)

            bold_elem.join(space)
            bold_elem.join(ref_tag)
            bold_elem.join(normal_elem)
            bold_elem.join(italic_elem)
            bold_elem.join(styled_bold_elem)
