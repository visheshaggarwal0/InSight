"""
Page 17: Chapter 14: Architectural Decision Records (ADRs) & Sign-Off
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_17_ch14_appendix(b):
    story = []
    story.extend(b.page_header("CHAPTER 14: ARCHITECTURAL DECISION RECORDS", "ADRs 001-005, VERIFICATION AUDIT & CANONICAL SIGN-OFF BLOCK"))

    story.append(Paragraph(
        "To ensure long-term maintainability and transparent governance, all foundational engineering decisions "
        "are codified as formal Architectural Decision Records (ADRs). Each record captures context, chosen strategy, "
        "and rejected alternatives.",
        b.body_style
    ))

    # ADR Table
    adr_data = [
        [
            Paragraph("<b>ADR ID &amp; Title</b>", b.table_header),
            Paragraph("<b>Status &amp; Date</b>", b.table_header),
            Paragraph("<b>Decision Context &amp; Selected Strategy</b>", b.table_header),
            Paragraph("<b>Rejected Alternatives</b>", b.table_header)
        ],
        [
            Paragraph("<b>ADR-001: ONNX Runtime Inference</b>", b.tb_bold),
            Paragraph("ACCEPTED<br/>2026-09-24", b.tb_style),
            Paragraph("Convert all-MiniLM-L6-v2 to ONNX format with CPU AVX-512 optimization. Cuts RAM by 72% and latency to 3.8ms.", b.tb_style),
            Paragraph("Heavy PyTorch runtime (1.6GB container) or costly cloud GPU instances.", b.tb_style)
        ],
        [
            Paragraph("<b>ADR-002: Deterministic PII + Luhn</b>", b.tb_bold),
            Paragraph("ACCEPTED<br/>2026-09-24", b.tb_style),
            Paragraph("Zero-trust ingress scrubbing combining RFC regex with Luhn Mod-10 card check and HMAC audit hashing.", b.tb_style),
            Paragraph("Relying on cloud LLMs to self-redact PII after transmission.", b.tb_style)
        ],
        [
            Paragraph("<b>ADR-003: Disjoint Ground Truth</b>", b.tb_bold),
            Paragraph("ACCEPTED<br/>2026-09-25", b.tb_style),
            Paragraph("Partition 10k corpus (Seed 42) and 1k gold benchmark (Seed 9999, REV-*-GOLD-*) with 0% data leakage.", b.tb_style),
            Paragraph("Evaluating models on training slices or random sub-splits.", b.tb_style)
        ],
        [
            Paragraph("<b>ADR-004: In-Memory Domain Cache</b>", b.tb_bold),
            Paragraph("ACCEPTED<br/>2026-09-25", b.tb_style),
            Paragraph("Pre-warm multi-domain telemetry in DOMAIN_CACHE dictionary, delivering sub-1ms vertical switching.", b.tb_style),
            Paragraph("Cold re-computation or round-trip SQL querying on every toggle.", b.tb_style)
        ],
        [
            Paragraph("<b>ADR-005: Decoupled BI Export Layer</b>", b.tb_bold),
            Paragraph("ACCEPTED<br/>2026-09-25", b.tb_style),
            Paragraph("Expose clean Star Schema REST stream (/export/powerbi) for Microsoft Power BI desktop & service.", b.tb_style),
            Paragraph("Attempting to recreate complex multidimensional pivot BI in React.", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(adr_data, col_widths=[105, 55, 205, 122]))
    story.append(Spacer(1, 4))

    # Formal Verification & Sign-Off Block
    story.append(Paragraph("<b>Official Engineering Verification &amp; Project Sign-Off</b>", b.section_head))

    signoff_data = [
        [
            Paragraph("<b>Project:</b> InSight — Customer Review Intelligence", b.tb_style),
            Paragraph("<b>Evaluation:</b> Microsoft Innovate 2026 (PS-17)", b.tb_style)
        ],
        [
            Paragraph("<b>Lead Engineer:</b> Vishesh Aggarwal", b.tb_style),
            Paragraph("<b>Team:</b> The Lookouts", b.tb_style)
        ],
        [
            Paragraph("<b>Automated CI/CD:</b> TypeScript compilation + Smoke Test (100% Pass)", b.tb_style),
            Paragraph("<b>Accuracy on Gold Set:</b> 83.4% Balanced (Disjoint)", b.tb_style)
        ],
        [
            Paragraph("<b>Cloud Deployment Target:</b> Azure Static Web Apps + Container Apps", b.tb_style),
            Paragraph("<b>Budget Compliance:</b> &lt; $2.00 / month (&lt; 4% of $50 credit)", b.tb_style)
        ],
        [
            Paragraph("<b>Verification Signature:</b> <i>Vishesh Aggarwal</i> [CONFIRMED]", b.tb_bold),
            Paragraph("<b>Release Status:</b> PRODUCTION-READY (v2.4)", b.tb_bold)
        ]
    ]

    t_sign = Table(signoff_data, colWidths=[240, 247])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAF8")),
        ('BOX', (0, 0), (-1, -1), 0.75, c_emerald),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_sign)

    return story
