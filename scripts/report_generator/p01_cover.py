"""
Page 1: Official Editorial Cover Page for InSight Technical Publication
"""
import os
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY,
    c_emerald, c_gold, c_slate_dark, c_slate_body, c_slate_muted, c_white, REPO_ROOT
)

def build_page_1_cover(b):
    story = []

    # Super-Header Institutional Metadata
    cover_agency = ParagraphStyle('CA', fontName=F_SANS_BOLD, fontSize=8.5, leading=11.0, textColor=c_emerald, alignment=TA_CENTER)
    cover_subagency = ParagraphStyle('CSA', fontName=F_SANS, fontSize=7.0, leading=9.0, textColor=c_slate_muted, alignment=TA_CENTER)
    cover_event = ParagraphStyle('CE', fontName=F_SANS_BOLD, fontSize=7.5, leading=9.5, textColor=c_gold, alignment=TA_CENTER)

    story.append(Paragraph("MICROSOFT INNOVATE 2026  |  ENTERPRISE AI HACKATHON", cover_agency))
    story.append(Paragraph("NATIONAL RESEARCH &amp; INDUSTRIAL APPLIED AI TASKFORCE", cover_subagency))
    story.append(Spacer(1, 4))
    story.append(Paragraph("PROBLEM STATEMENT 17  |  10,000 REVIEWS, NO TIME TO READ THEM", cover_event))
    story.append(Spacer(1, 14))

    # InSight Branding Logo
    logo_path = os.path.join(REPO_ROOT, "frontend", "public", "insight-logo.png")
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=88, height=88))
    else:
        logo_placeholder = Paragraph("<b>INSIGHT</b>", ParagraphStyle('LP', fontName=F_TITLE, fontSize=28, leading=32, textColor=c_emerald, alignment=TA_CENTER))
        story.append(logo_placeholder)

    story.append(Spacer(1, 12))

    # Main Publication Titles
    title_p = Paragraph(
        "INSIGHT: CANONICAL ENGINEERING MONOGRAPH",
        ParagraphStyle('MainTitle', fontName=F_TITLE, fontSize=18.5, leading=22.5, textColor=c_slate_dark, alignment=TA_CENTER)
    )
    story.append(title_p)
    story.append(Spacer(1, 4))

    doc_sub = Paragraph(
        "System Architecture, Real-Time Statistical Telemetry &amp; Transformer NLP Codex",
        ParagraphStyle('DocSub', fontName=F_SANS_BOLD, fontSize=10.5, leading=13.5, textColor=c_emerald, alignment=TA_CENTER)
    )
    story.append(doc_sub)
    story.append(Spacer(1, 6))

    sub_p = Paragraph(
        "Transforming 10,000 Unstructured Multi-Platform Customer Reviews into Real-Time Defect Detection, "
        "Contrastive Clause-Level Sentiment, Statistically Calibrated Relative Risk (RR), Population Stability Index (PSI) Drift Monitoring, "
        "and Automated Microsoft Phi-3-mini Jira Incident Remediation via Zero-Trust ONNX Serverless Pipelines.",
        ParagraphStyle('SubTitle', fontName=F_BODY, fontSize=7.8, leading=11.2, textColor=c_slate_muted, alignment=TA_CENTER)
    )
    story.append(sub_p)
    story.append(Spacer(1, 14))

    # Metadata Grid (Authors, Architecture, Platforms, Stack)
    lead_cell_bold = ParagraphStyle('LCB', fontName=F_SANS_BOLD, fontSize=7.5, leading=9.5, textColor=c_slate_dark)
    lead_cell_norm = ParagraphStyle('LCN', fontName=F_SANS, fontSize=7.2, leading=9.2, textColor=c_slate_body)
    lead_data = [
        [
            Paragraph("<b>Core Author &amp; Lead:</b> Vishesh Aggarwal", lead_cell_bold),
            Paragraph("<b>System Topology:</b> Decoupled Serverless / FastAPI + React 19", lead_cell_bold)
        ],
        [
            Paragraph("<b>Team:</b> The Lookouts", lead_cell_norm),
            Paragraph("<b>NLP Inference Engine:</b> Microsoft ONNX Runtime (all-MiniLM-L6-v2)", lead_cell_norm)
        ],
        [
            Paragraph("<b>Hackathon Challenge:</b> Innovate PS-17 (Customer Feedback)", lead_cell_norm),
            Paragraph("<b>Unsupervised Geometry:</b> UMAP Manifolds + HDBSCAN + c-TF-IDF", lead_cell_norm)
        ],
        [
            Paragraph("<b>Cloud Environment:</b> Azure Static Web Apps + Container Apps", lead_cell_norm),
            Paragraph("<b>BI Bridge:</b> Live OData/REST Feed to Microsoft Power BI Desktop", lead_cell_norm)
        ]
    ]
    t_lead = Table(lead_data, colWidths=[240, 247])
    t_lead.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAF8")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7.0),
    ]))
    story.append(t_lead)
    story.append(Spacer(1, 12))

    # Quick Stats Metric Banner
    story.append(b.metric_banner([
        ("10,000", "Corpus Reviews Indexed"),
        ("384-Dim", "Dense Semantic Embedding Space"),
        ("&lt; 1 ms", "In-Memory Domain Partition Switching"),
        ("100% Zero-Leak", "Gold Standard Evaluation Set")
    ], pad=4.5))
    story.append(Spacer(1, 14))

    # Executive Abstract Callout
    story.append(b.callout(
        "EXECUTIVE CODEX PREFACE // THE ENTERPRISE FEEDBACK CRISIS",
        "Modern consumer enterprises ingest tens of thousands of customer reviews weekly across Amazon, Shopify, App Stores, "
        "and Zendesk tickets. Traditional text analytics relies on monolithic LLM prompt chains that exhaust token budgets and hallucinate, "
        "or obsolete unigram TF-IDF bag-of-words models that fail to parse concessive clauses ('The camera is great, but the battery died'). "
        "InSight establishes an industrial-grade, zero-trust analytical bridge: combining deterministic regex PII scrubbers, "
        "linguistic contrastive span extraction, Microsoft ONNX embedding projections, noise-free density clustering, "
        "and calibrated epidemiological Relative Risk (RR) scores. Telemetry is streamed directly into Microsoft Power BI for corporate governance, "
        "while critical production bugs are escalated into Jira tickets via Microsoft Phi-3-mini on demand.",
        pad=6.5
    ))
    story.append(Spacer(1, 16))

    # Security & Verification Footer Block
    footer_data = [
        [
            Paragraph("<b>Classification:</b> RESTRICTED // TECHNICAL MONOGRAPH", b.meta_style),
            Paragraph("<b>Target Audience:</b> VP Engineering, Head of Product, Data Science Lead", b.meta_style),
            Paragraph("<b>Revision:</b> v2.4 (Production Release)", b.meta_style)
        ]
    ]
    t_foot = Table(footer_data, colWidths=[162, 205, 120])
    t_foot.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_foot)

    return story
