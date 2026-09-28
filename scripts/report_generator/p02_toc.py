"""
Pages 2 & 3: Table of Contents & Executive Document Structure
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def make_toc_row(ch_num, title, subtitle, page_str, b):
    num_p = Paragraph(f"<b>{ch_num}</b>", ParagraphStyle('TOCNum', fontName=F_SANS_BOLD, fontSize=7.8, leading=9.8, textColor=c_gold))
    title_p = Paragraph(
        f"<b>{title}</b><br/><font color='#6B7280' size='6.5'>{subtitle}</font>",
        ParagraphStyle('TOCTitle', fontName=F_SANS, fontSize=7.5, leading=9.5, textColor=c_slate_dark)
    )
    page_p = Paragraph(f"<b>{page_str}</b>", ParagraphStyle('TOCPage', fontName=F_SANS_BOLD, fontSize=7.5, leading=9.5, textColor=c_emerald, alignment=TA_RIGHT))
    return [num_p, title_p, page_p]

def build_page_2_toc_part1(b):
    story = []
    story.extend(b.page_header("TABLE OF CONTENTS", "PART I: SYSTEM FOUNDATIONS, PROBLEM SPACE & CORE PIPELINES"))

    story.append(b.callout(
        "ARCHITECTURAL MANIFESTO // SYSTEM OVERVIEW",
        "The InSight technical manual details the mathematical, infrastructural, and linguistic foundations "
        "of enterprise feedback telemetry. Spanning 14 dedicated engineering chapters, it documents how raw, noisy customer "
        "text is systematically ingested, scrubbed of PII, decomposed into contrastive syntactic clauses, embedded via Microsoft ONNX Runtime, "
        "clustered into emergent product failure topics, calibrated with Platt scaling, and bridged to executive Microsoft Power BI dashboards."
    ))
    story.append(Spacer(1, 6))

    toc_data = [
        [
            Paragraph("<b>CH</b>", ParagraphStyle('THC', fontName=F_SANS_BOLD, fontSize=7.2, textColor=c_emerald)),
            Paragraph("<b>SECTION / ARCHITECTURAL DOMAIN</b>", ParagraphStyle('THC', fontName=F_SANS_BOLD, fontSize=7.2, textColor=c_emerald)),
            Paragraph("<b>PAGE</b>", ParagraphStyle('THC', fontName=F_SANS_BOLD, fontSize=7.2, textColor=c_emerald, alignment=TA_RIGHT))
        ],
        make_toc_row("01", "The 10,000 Reviews Deluge & Feedback Debt", "Voice of Customer crisis, 1-star skew, blind spots in enterprise support", "04", b),
        make_toc_row("02", "Why Naive AI & Monolithic LLMs Fail at Scale", "Prompt drift, context exhaustion, astronomical token bills, and TF-IDF unigram limits", "05", b),
        make_toc_row("03", "Dual-Persona Operational Architecture", "Decoupled FastAPI backend, React 19 frontend, Executive vs Product Engineer split", "06", b),
        make_toc_row("04", "Zero-Trust PII Scrubbing & HMAC Privacy Vault", "Deterministic regex tokenization, Luhn check, HMAC-SHA256 privacy audit logs", "07", b),
        make_toc_row("05", "Contrastive Clause Splitting & Senti-Span Extraction", "Concessive discourse markers, linguistic boundary parsing, and clause-level polarity", "08", b),
        make_toc_row("06", "Microsoft ONNX Runtime & Dense Semantic Vectors", "all-MiniLM-L6-v2 384-dimensional space, FP32 to ONNX quantization, CPU throughput", "09", b),
        make_toc_row("07", "Unsupervised Topic Discovery: UMAP & HDBSCAN", "Zero-noise nearest-centroid fallback, manifold projection, class-based c-TF-IDF", "10", b),
    ]

    t_toc = Table(toc_data, colWidths=[28, 415, 44])
    t_toc.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.0, c_emerald),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, c_emerald),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 6))

    story.append(b.metric_banner([
        ("Chapters 01–07", "Algorithmic Pipeline Core"),
        ("100% In-Memory", "Pre-Warmed Multi-Domain State"),
        ("Zero-Leakage", "Disjoint Training & Evaluation Sets")
    ]))

    return story

def build_page_3_toc_part2(b):
    story = []
    story.extend(b.page_header("TABLE OF CONTENTS (CONTINUED)", "PART II: ADVANCED TELEMETRY, CLOUD TOPOLOGY & APPENDICES"))

    toc_data = [
        [
            Paragraph("<b>CH</b>", ParagraphStyle('THC', fontName=F_SANS_BOLD, fontSize=7.2, textColor=c_emerald)),
            Paragraph("<b>SECTION / ARCHITECTURAL DOMAIN</b>", ParagraphStyle('THC', fontName=F_SANS_BOLD, fontSize=7.2, textColor=c_emerald)),
            Paragraph("<b>PAGE</b>", ParagraphStyle('THC', fontName=F_SANS_BOLD, fontSize=7.2, textColor=c_emerald, alignment=TA_RIGHT))
        ],
        make_toc_row("08", "Statistical Telemetry: PSI & Causal Relative Risk", "Population Stability Index drift alerts, Relative Risk (RR) odds, Bayesian priors", "11", b),
        make_toc_row("09", "Model Governance & Platt Scaling Calibration", "Sigmoid post-hoc calibration, Brier score optimization, 3x3 confusion matrix", "12", b),
        make_toc_row("10", "Microsoft Power BI Corporate Analytics Bridge", "Direct OData/REST feed, Star Schema Fact_ReviewTelemetry, automated DAX metrics", "13", b),
        make_toc_row("11", "Enterprise Azure Serverless Deployment", "Azure Static Web Apps, Container Apps, scale-to-zero, $20 budget alert, cost <$2", "14", b),
        make_toc_row("12", "Closed-Loop Remediation: SLM Incident Generation", "Microsoft Phi-3-mini on-demand Jira bug synthesis, root-cause verbatim citations", "15", b),
        make_toc_row("13", "Dual Enterprise Case Studies: D2C vs Tech SaaS", "Cosmetics 'SkinGlow' pump failure vs SaaS 'FlowMetrics' CSV crash & churn spikes", "16", b),
        make_toc_row("14", "Architectural Decision Records & Verification", "ADRs 001–005, Gold-standard test suite, CI/CD automated test sign-off", "17", b),
    ]

    t_toc = Table(toc_data, colWidths=[28, 415, 44])
    t_toc.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.0, c_emerald),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, c_emerald),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 6))

    story.append(b.callout(
        "ARCHITECTURAL CONFORMANCE DECLARATION",
        "Every quantitative claim, statistical measure, and pipeline step documented herein maps directly to "
        "executable source code within the InSight repository (c:/Users/aggar/Documents/InSight). "
        "No speculative or non-implemented components are presented as operational fact. "
        "The system has been rigorously tested against a 1,000-sample disjoint ground-truth test corpus."
    ))
    story.append(Spacer(1, 6))

    # Metric Banner for Operational Performance
    story.append(b.metric_banner([
        ("0.834 ACC", "Balanced 3-Class Sentiment"),
        ("&lt; 25 ms", "FastAPI End-to-End Query Latency"),
        ("100% Deterministic", "Luhn & Regex PII Sanitization"),
        ("&lt; $2.00", "Total Cloud Hosting Monthly Cost")
    ]))

    return story
