"""
InSight Technical Publication — Styles, Typography & Flowable Helpers
Design system and layout components for publication-grade ReportLab PDF generation.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# Repository Root Resolution
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Font Registration with System Fonts & Fallbacks
FONT_DIR = "C:/Windows/Fonts"
try:
    pdfmetrics.registerFont(TTFont('Georgia', f'{FONT_DIR}/georgia.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia-Bold', f'{FONT_DIR}/georgiab.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia-Italic', f'{FONT_DIR}/georgiai.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia-BoldItalic', f'{FONT_DIR}/georgiaz.ttf'))

    pdfmetrics.registerFont(TTFont('SegoeUI', f'{FONT_DIR}/segoeui.ttf'))
    pdfmetrics.registerFont(TTFont('SegoeUI-Bold', f'{FONT_DIR}/segoeuib.ttf'))
    pdfmetrics.registerFont(TTFont('SegoeUI-SemiBold', f'{FONT_DIR}/seguisb.ttf'))
    pdfmetrics.registerFont(TTFont('SegoeUI-Italic', f'{FONT_DIR}/segoeuii.ttf'))

    pdfmetrics.registerFont(TTFont('Consolas', f'{FONT_DIR}/consola.ttf'))
    pdfmetrics.registerFont(TTFont('Consolas-Bold', f'{FONT_DIR}/consolab.ttf'))

    registerFontFamily('Georgia', normal='Georgia', bold='Georgia-Bold', italic='Georgia-Italic', boldItalic='Georgia-BoldItalic')
    registerFontFamily('SegoeUI', normal='SegoeUI', bold='SegoeUI-Bold', italic='SegoeUI-Italic', boldItalic='SegoeUI-Bold')
    registerFontFamily('Consolas', normal='Consolas', bold='Consolas-Bold', italic='Consolas', boldItalic='Consolas-Bold')

    F_BODY = 'Georgia'
    F_BODY_BOLD = 'Georgia-Bold'
    F_BODY_ITALIC = 'Georgia-Italic'
    F_SANS = 'SegoeUI'
    F_SANS_BOLD = 'SegoeUI-Bold'
    F_SANS_SEMI = 'SegoeUI-SemiBold'
    F_TITLE = 'Georgia-Bold'
    F_CODE = 'Consolas'
    F_CODE_BOLD = 'Consolas-Bold'
except Exception:
    F_BODY = 'Times-Roman'
    F_BODY_BOLD = 'Times-Bold'
    F_BODY_ITALIC = 'Times-Italic'
    F_SANS = 'Helvetica'
    F_SANS_BOLD = 'Helvetica-Bold'
    F_SANS_SEMI = 'Helvetica-Bold'
    F_TITLE = 'Times-Bold'
    F_CODE = 'Courier'
    F_CODE_BOLD = 'Courier-Bold'

# InSight Emerald & Executive Palette
c_emerald = colors.HexColor("#0F382E")        # Primary Deep Brand Emerald
c_emerald_accent = colors.HexColor("#10B981") # Vibrant UI Emerald
c_emerald_light = colors.HexColor("#ECFDF5")  # Soft Emerald Wash
c_gold = colors.HexColor("#D97706")           # Accent Gold / Amber
c_gold_light = colors.HexColor("#FFFBEB")     # Soft Amber Wash
c_slate_dark = colors.HexColor("#111827")     # Charcoal Dark Headings
c_slate_body = colors.HexColor("#374151")     # Body Text Charcoal
c_slate_muted = colors.HexColor("#6B7280")    # Subtitle / Muted Meta
c_border = colors.HexColor("#E5E7EB")         # Gray Border Rule
c_bg_callout = colors.HexColor("#F8FAF8")     # Off-White Card Tint
c_bg_code = colors.HexColor("#F3F4F6")        # Code Block Background
c_white = colors.HexColor("#FFFFFF")
c_danger = colors.HexColor("#EF4444")        # Defect / Critical Red
c_bg_danger = colors.HexColor("#FEF2F2")

class NumberedCanvas(canvas.Canvas):
    """Two-pass running header and footer canvas with total page calculation."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress running decorations on cover page

        page_w, page_h = A4
        margin = 54.0

        self.saveState()

        # Running Header
        self.setFont(F_SANS_BOLD, 7.0)
        self.setFillColor(c_emerald)
        self.drawString(margin, page_h - 32, "INSIGHT")

        self.setFont(F_SANS, 7.0)
        self.setFillColor(c_slate_muted)
        self.drawString(margin + 42, page_h - 32, " |  UNIVERSAL REVIEW INTELLIGENCE & TELEMETRY CODEX")
        self.drawRightString(page_w - margin, page_h - 32, "MICROSOFT INNOVATE  |  CHALLENGE 17")

        # Header Hairline Rule
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.5)
        self.line(margin, page_h - 38, page_w - margin, page_h - 38)

        # Footer Hairline Rule
        self.setStrokeColor(c_border)
        self.setLineWidth(0.5)
        self.line(margin, 44, page_w - margin, 44)

        # Running Footer
        self.setFont(F_SANS_BOLD, 7.0)
        self.setFillColor(c_emerald)
        self.drawString(margin, 32, "CONFIDENTIAL // OFFICIAL TECHNICAL & ENGINEERING MONOGRAPH")

        self.setFont(F_SANS, 7.0)
        self.setFillColor(c_slate_muted)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(page_w - margin, 32, page_str)

        self.restoreState()


class StylesBundle:
    """Encapsulates typography styles, colors, and layout metrics."""
    def __init__(self, printable_width=487.27):
        self.pw = printable_width
        self.styles = getSampleStyleSheet()

        # Base Typography
        self.chapter_num = ParagraphStyle(
            'ChNum', fontName=F_SANS_BOLD, fontSize=8.5, leading=11.0,
            textColor=c_gold, spaceAfter=2
        )
        self.chapter_title = ParagraphStyle(
            'ChTitle', fontName=F_TITLE, fontSize=15.0, leading=18.5,
            textColor=c_slate_dark, spaceAfter=3
        )
        self.section_subtitle = ParagraphStyle(
            'ChSub', fontName=F_SANS_SEMI, fontSize=8.5, leading=11.5,
            textColor=c_slate_muted, spaceAfter=6
        )
        self.section_head = ParagraphStyle(
            'SecHead', fontName=F_SANS_BOLD, fontSize=9.5, leading=12.5,
            textColor=c_emerald, spaceBefore=8, spaceAfter=4
        )
        self.subsection_head = ParagraphStyle(
            'SubSecHead', fontName=F_SANS_BOLD, fontSize=8.5, leading=11.0,
            textColor=c_slate_dark, spaceBefore=5, spaceAfter=3
        )
        self.body_style = ParagraphStyle(
            'Body', fontName=F_BODY, fontSize=8.2, leading=11.8,
            textColor=c_slate_body, alignment=TA_JUSTIFY, spaceAfter=4
        )
        self.body_bold = ParagraphStyle(
            'BodyBold', parent=self.body_style, fontName=F_BODY_BOLD
        )
        self.bullet_style = ParagraphStyle(
            'Bullet', fontName=F_BODY, fontSize=8.0, leading=11.2,
            textColor=c_slate_body, leftIndent=12, firstLineIndent=-8, spaceAfter=3
        )
        self.callout_text = ParagraphStyle(
            'CalloutText', fontName=F_BODY, fontSize=8.0, leading=11.2,
            textColor=c_slate_body
        )
        self.code_style = ParagraphStyle(
            'CodeText', fontName=F_CODE, fontSize=7.2, leading=9.5,
            textColor=colors.HexColor("#1F2937")
        )
        self.table_header = ParagraphStyle(
            'TH', fontName=F_SANS_BOLD, fontSize=7.5, leading=9.5,
            textColor=c_white, alignment=TA_CENTER
        )
        self.table_cell = ParagraphStyle(
            'TC', fontName=F_SANS, fontSize=7.2, leading=9.2,
            textColor=c_slate_body, alignment=TA_LEFT
        )
        self.table_cell_bold = ParagraphStyle(
            'TCB', fontName=F_SANS_BOLD, fontSize=7.2, leading=9.2,
            textColor=c_slate_dark, alignment=TA_LEFT
        )
        self.table_cell_center = ParagraphStyle(
            'TCC', fontName=F_SANS, fontSize=7.2, leading=9.2,
            textColor=c_slate_body, alignment=TA_CENTER
        )
        # Convenience aliases
        self.tb_style = self.table_cell
        self.tb_bold = self.table_cell_bold
        self.th_style = ParagraphStyle(
            'THForest', fontName=F_SANS_BOLD, fontSize=7.2, leading=9.2,
            textColor=c_emerald
        )
        self.meta_style = ParagraphStyle(
            'Meta', fontName=F_SANS, fontSize=7.0, leading=9.0, textColor=c_slate_muted
        )

    def section_divider(self, color=colors.HexColor("#CBD5E1"), thickness=0.5, space=4):
        return HRFlowable(width="100%", thickness=thickness, color=color, spaceBefore=space, spaceAfter=space)

    def page_header(self, chapter_title, section_subtitle=None):
        flowables = [
            Paragraph(chapter_title, self.chapter_title)
        ]
        if section_subtitle:
            flowables.append(Paragraph(section_subtitle, self.section_subtitle))
        flowables.append(self.section_divider(space=3))
        return flowables

    def callout(self, title, body_text, accent=c_emerald, bg=c_bg_callout, title_fs=7.5, body_fs=7.8, pad=5.0):
        title_p = Paragraph(f"<b>{title.upper()}</b>", ParagraphStyle('CT', fontName=F_SANS_BOLD, fontSize=title_fs, leading=title_fs+2.5, textColor=accent, spaceAfter=2.5))
        body_p = Paragraph(body_text, ParagraphStyle('CB', fontName=F_BODY, fontSize=body_fs, leading=body_fs+3.2, textColor=c_slate_body))
        t = Table([[title_p], [body_p]], colWidths=[self.pw])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('LINEBEFORE', (0, 0), (0, -1), 3.0, accent),
            ('BOX', (0, 0), (-1, -1), 0.5, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), pad),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    def code_box(self, code_text, label="ARCHITECTURAL SPECIFICATION", fs=6.5, lead=8.5, pad=5.0):
        escaped = (
            code_text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br/>')
            .replace(' ', '&nbsp;')
        )
        label_p = Paragraph(f"<b>[ {label} ]</b>", ParagraphStyle('CL', fontName=F_SANS_BOLD, fontSize=6.5, leading=8.0, textColor=c_emerald, spaceAfter=2))
        code_p = Paragraph(escaped, ParagraphStyle('CBX', fontName=F_CODE, fontSize=fs, leading=lead, textColor=c_slate_dark))
        t = Table([[label_p], [code_p]], colWidths=[self.pw])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_bg_code),
            ('LINEBEFORE', (0, 0), (0, -1), 2.5, c_emerald),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), pad),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    def booktabs_table(self, data, col_widths, th_bg=c_emerald, is_striped=True, pad=3.2):
        t = Table(data, colWidths=col_widths)
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), th_bg),
            ('LINEABOVE', (0, 0), (-1, 0), 1.0, c_emerald),
            ('LINEBELOW', (0, 0), (-1, 0), 0.75, c_emerald),
            ('LINEBELOW', (0, -1), (-1, -1), 0.75, colors.HexColor("#94A3B8")),
            ('TOPPADDING', (0, 0), (-1, -1), pad),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
            ('LEFTPADDING', (0, 0), (-1, -1), 4.0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4.0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        if is_striped and len(data) > 1:
            style.append(('ROWBACKGROUNDS', (0, 1), (-1, -1), [c_white, colors.HexColor("#F8FAFC")]))
        t.setStyle(TableStyle(style))
        return t

    def metric_banner(self, metrics, col_widths=None, pad=3.0):
        if col_widths is None:
            col_widths = [self.pw / len(metrics)] * len(metrics)
        cells = []
        for val, lbl in metrics:
            val_p = Paragraph(f"<b>{val}</b>", ParagraphStyle('MV', fontName=F_SANS_BOLD, fontSize=9.5, leading=11.5, textColor=c_emerald, alignment=TA_CENTER))
            lbl_p = Paragraph(lbl, ParagraphStyle('ML', fontName=F_SANS, fontSize=6.5, leading=7.8, textColor=c_slate_muted, alignment=TA_CENTER))
            cells.append([val_p, lbl_p])
        t = Table([cells], colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAF8")),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#D1FAE5")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), pad),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    def make_callout(self, text, title="INSIGHT ARCHITECTURAL TAKEAWAY", bg=c_bg_callout, border=c_emerald, width=None):
        """Creates a professional callout box with accent left border."""
        return self.callout(title=title, body_text=text, accent=border, bg=bg)

    def make_badge_table(self, col1_title, col1_desc, col2_title, col2_desc, width=None):
        """Creates a side-by-side executive card pair."""
        w = (width or self.pw) / 2.0 - 4
        c1 = [
            [Paragraph(f"<b>{col1_title}</b>", self.table_cell_bold)],
            [Paragraph(col1_desc, self.body_style)]
        ]
        c2 = [
            [Paragraph(f"<b>{col2_title}</b>", self.table_cell_bold)],
            [Paragraph(col2_desc, self.body_style)]
        ]
        t1 = Table(c1, colWidths=[w])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_bg_callout),
            ('BOX', (0,0), (-1,-1), 0.5, c_border),
            ('PADDING', (0,0), (-1,-1), 5)
        ]))
        t2 = Table(c2, colWidths=[w])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_bg_callout),
            ('BOX', (0,0), (-1,-1), 0.5, c_border),
            ('PADDING', (0,0), (-1,-1), 5)
        ]))
        wrapper = Table([[t1, '', t2]], colWidths=[w, 8, w])
        wrapper.setStyle(TableStyle([
            ('PADDING', (0,0), (-1,-1), 0),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        return wrapper
