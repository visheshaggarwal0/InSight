"""
Page 8: Chapter 5: Contrastive Clause Splitting & Senti-Span Extraction
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_8_ch5_clause_parsing(b):
    story = []
    story.extend(b.page_header("CHAPTER 05: CONTRASTIVE CLAUSE PARSING", "DISCOURSE MARKER BOUNDARIES, SENTI-SPAN OFFSETS & CONCESSIVE DEFECT EXTRACTION"))

    story.append(Paragraph(
        "A foundational blind spot in commercial sentiment analysis is the assumption of document-level sentiment uniformity. "
        "Consumer feedback is intrinsically contrastive: customers routinely open with flattering praise before pivoting to an "
        "aggravating product failure. For example: <i>'The facial cream feels luxurious and absorbs instantly, <b>but the pump mechanism broke on day three and won't dispense any serum</b>.'</i> "
        "When treated as an atomic text, positive tokens ('luxurious', 'instantly') cancel out the negative clause, yielding a benign 'Neutral' score. "
        "The critical hardware defect remains invisible to QA teams.",
        b.body_style
    ))

    story.append(b.callout(
        "THE CONCESSIVE CAMOUFLAGE HAZARD",
        "Document-level sentiment classification operates as a low-pass filter: high-frequency positive compliments drown out "
        "sharp, low-frequency negative failure clauses. InSight implements a deterministic <b>Linguistic Clause Splitter</b> "
        "that parses discourse trees across adversative markers to extract exact character-offset defect spans."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Contrastive Discourse Markers (CDMs) & Syntactic Splitting</b>", b.section_head))
    story.append(Paragraph(
        "InSight monitors a canonical inventory of contrastive discourse markers: "
        "<font name='Consolas'>[ 'but', 'however', 'except that', 'although', 'yet', 'nevertheless', 'on the other hand', 'though', 'unfortunately' ]</font>. "
        "When a contrastive boundary is detected, the review is bifurcated into its subordinate concessive clause and matrix clause. "
        "The downstream complaint span is isolated with exact start and end string offsets (<font name='Consolas'>(start_idx, end_idx)</font>). "
        "The frontend verbatim drawer consumes these offsets to wrap the defect in an ambient amber-red <font name='Consolas'>&lt;mark&gt;</font> highlight, "
        "allowing engineers to read the defect in 200 milliseconds without parsing the preamble.",
        b.body_style
    ))

    # Clause Extraction Code Box
    clause_code = (
        "def extract_complaint_span(text: str) -> tuple[str, int, int]:\n"
        "    \"\"\"Extracts the adversative complaint clause and character offsets.\"\"\"\n"
        "    cdm_pattern = re.compile(r'\\b(but|however|except that|although|yet|unfortunately)\\b', re.IGNORECASE)\n"
        "    match = cdm_pattern.search(text)\n"
        "    if match:\n"
        "        start_idx = match.start()\n"
        "        span_text = text[start_idx:].strip()\n"
        "        return span_text, start_idx, len(text)\n"
        "    return text, 0, len(text)"
    )
    story.append(b.code_box(clause_code, label="CONTRASTIVE DISCOURSE EXTRACTION ENGINE"))
    story.append(Spacer(1, 4))

    # Empirical Comparison Table
    story.append(Paragraph("<b>Empirical Performance: Whole-Review vs. Contrastive Clause Extraction</b>", b.subsection_head))
    comp_data = [
        [
            Paragraph("<b>Sample Customer Review Verbatim</b>", b.table_header),
            Paragraph("<b>Document-Level Model</b>", b.table_header),
            Paragraph("<b>InSight Clause Extractor</b>", b.table_header),
            Paragraph("<b>Operational Outcome</b>", b.table_header)
        ],
        [
            Paragraph("<i>'Formula smells wonderful and glides on skin, but the dropper cracked inside the bottle.'</i>", b.tb_style),
            Paragraph("Sentiment: <b>Neutral</b> (0.52)<br/>Action: None (Dismissed)", b.tb_style),
            Paragraph("Span: <i>'but the dropper cracked inside the bottle'</i> (Neg: 0.94)", b.tb_style),
            Paragraph("<b>P0 Packaging Defect Alert</b> routed to QA", b.tb_style)
        ],
        [
            Paragraph("<i>'Incredible UI design and dashboard speed, however CSV exports timeout after 500 rows.'</i>", b.tb_style),
            Paragraph("Sentiment: <b>Positive</b> (0.71)<br/>Action: None (Dismissed)", b.tb_style),
            Paragraph("Span: <i>'however CSV exports timeout after 500 rows'</i> (Neg: 0.89)", b.tb_style),
            Paragraph("<b>Database Index Bug</b> filed into Jira", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(comp_data, col_widths=[170, 105, 125, 87]))
    story.append(Spacer(1, 4))

    story.append(b.metric_banner([
        ("94.2% Precision", "Adversative Clause Extraction"),
        ("0.0 ms Latency", "Deterministic Regex Parsing"),
        ("&lt;mark&gt; Highlighting", "Live Verbatim Visualizer"),
        ("Zero Washout", "Defect Camouflage Eliminated")
    ]))

    return story
