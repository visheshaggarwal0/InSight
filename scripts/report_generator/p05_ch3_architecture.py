"""
Page 6: Chapter 3: Dual-Persona Architecture & System Topology
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

from .charts import create_architecture_diagram

def build_page_6_ch3_architecture(b):
    story = []
    story.extend(b.page_header("CHAPTER 03: SYSTEM TOPOLOGY & DUAL PERSONAS", "DECOUPLED ARCHITECTURE, FASTAPI IN-MEMORY CACHE & DUAL-PERSONA WORKFLOWS"))

    story.append(Paragraph(
        "A critical failure of typical analytics tools is cognitive impedance mismatch: enterprise leadership requires high-level "
        "macro-economic telemetry (NSS trends, channel churn exposure, month-over-month volume shifts), while software and hardware "
        "reliability engineers require granular clause-level verbatims, stack traces, and reproducible bug tickets. "
        "InSight resolves this via a <b>Dual-Persona Operational Architecture</b> built upon a decoupled React 19 and FastAPI core.",
        b.body_style
    ))

    # Side-by-side Badge Table for Dual Personas
    story.append(b.make_badge_table(
        "1. Executive & Business Leadership Persona",
        "• High-Level Overview: 30-day sentiment trajectory & volume spikes.<br/>"
        "• Risk Attribution: Relative Risk (RR) scores across marketing channels.<br/>"
        "• Power BI Integration: Native OData Star Schema export for corporate BI.<br/>"
        "• Longitudinal Health: Population Stability Index (PSI) drift tracking.",
        "2. Product & Reliability Engineering Persona",
        "• Clause-Level Verbatims: Exact contrastive complaint isolation.<br/>"
        "• Defect Centroids: Unsupervised cluster drill-down with zero noise.<br/>"
        "• Phi-3-mini Bug Tickets: Instant Jira-ready defect markdown with citations.<br/>"
        "• PII Masking: Live toggle between raw verbatims and sanitized audit views."
    ))
    story.append(Spacer(1, 5))

    story.append(Paragraph("<b>Decoupled System Architecture Specification</b>", b.section_head))
    story.append(Paragraph(
        "The InSight codebase is partitioned into an asynchronous high-performance Python FastAPI service "
        "(<font name='Consolas'>backend/app/</font>) and a typed React 19 Single Page Application (<font name='Consolas'>frontend/src/</font>). "
        "Communication occurs exclusively over strongly-typed RESTful JSON interfaces defined by Pydantic v2 schemas.",
        b.body_style
    ))
    story.append(Spacer(1, 4))

    # Vector Architecture Graphic
    story.append(create_architecture_diagram(width=b.pw, height=115))
    story.append(Spacer(1, 6))

    # Table of Core Endpoints
    story.append(Paragraph("<b>Core API Gateway Interface Specifications</b>", b.subsection_head))
    api_data = [
        [
            Paragraph("<b>HTTP Route</b>", b.table_header),
            Paragraph("<b>HTTP Method</b>", b.table_header),
            Paragraph("<b>Payload / Response Signature</b>", b.table_header),
            Paragraph("<b>Latency SLA</b>", b.table_header)
        ],
        [
            Paragraph("<b>/api/overview</b>", b.tb_bold),
            Paragraph("GET", b.tb_style),
            Paragraph("NSS, 30d trend points, channel sentiment, source breakdown", b.tb_style),
            Paragraph("&lt; 5 ms", b.tb_style)
        ],
        [
            Paragraph("<b>/api/clusters</b>", b.tb_bold),
            Paragraph("GET", b.tb_style),
            Paragraph("Cluster array with label, size, centroid, keywords, sample verbatims", b.tb_style),
            Paragraph("&lt; 8 ms", b.tb_style)
        ],
        [
            Paragraph("<b>/api/reviews</b>", b.tb_bold),
            Paragraph("GET", b.tb_style),
            Paragraph("Filtered paginated review records with contrastive spans & PII state", b.tb_style),
            Paragraph("&lt; 12 ms", b.tb_style)
        ],
        [
            Paragraph("<b>/api/generate_ticket</b>", b.tb_bold),
            Paragraph("POST", b.tb_style),
            Paragraph("Phi-3-mini Jira ticket markdown with defect classification", b.tb_style),
            Paragraph("&lt; 850 ms", b.tb_style)
        ],
        [
            Paragraph("<b>/api/export/powerbi</b>", b.tb_bold),
            Paragraph("GET", b.tb_style),
            Paragraph("Normalized Star Schema tabular stream for Power BI Web Connector", b.tb_style),
            Paragraph("&lt; 20 ms", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(api_data, col_widths=[95, 45, 275, 72]))

    return story
