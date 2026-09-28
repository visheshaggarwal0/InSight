"""
Page 4: Chapter 1: The 10,000 Reviews Deluge & Feedback Debt
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_4_ch1_crisis(b):
    story = []
    story.extend(b.page_header("CHAPTER 01: THE 10,000 REVIEWS DELUGE", "THE ENTERPRISE FEEDBACK CRISIS, SILENT CHURN & COGNITIVE FATIGUE"))

    story.append(Paragraph(
        "Modern digital enterprises operate across fragmented multi-channel feedback ecosystems: mobile application stores "
        "(Apple App Store, Google Play), e-commerce marketplaces (Amazon, Shopify), public review aggregators (Trustpilot, G2), "
        "and internal customer support queues (Zendesk, Freshdesk, Intercom). An enterprise generating 10,000 customer reviews "
        "monthly faces a structural processing bottleneck: human reading speed averages 250 words per minute, requiring over "
        "330 continuous human analyst hours simply to read raw text without performing cross-cohort statistical aggregation or root-cause synthesis.",
        b.body_style
    ))

    story.append(b.callout(
        "THE FEEDBACK DEBT PHENOMENON",
        "Feedback Debt represents the cumulative backlog of unanalyzed customer pain points that directly drive silent customer churn. "
        "Because 96% of unhappy customers never file a formal support ticket—preferring instead to post a passing review or abandon the product—"
        "organizations relying solely on customer success tickets operate with an 80% blind spot regarding product defects."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>The Four Structural Blind Spots of Conventional Review Triage</b>", b.section_head))

    story.append(Paragraph(
        "<b>1. Star-Rating Deception & Concessive Camouflage:</b> A customer leaving a 4-star review often embeds a severe production defect: "
        "<i>'Love the hydration serum, but the glass dropper shattered on my bathroom counter.'</i> Because product teams filter reviews "
        "strictly for 1-star and 2-star ratings, critical safety, packaging, and billing defects slip past monitoring systems.<br/>"
        "<b>2. Multi-Channel Fragmented Schemas:</b> Amazon formats differ from App Store crash logs; Zendesk tickets contain agent replies; "
        "social feeds contain emoji-dense slang. Without unified ingestion normalization, holistic cross-platform analysis is impossible.<br/>"
        "<b>3. PII Compliance Liability:</b> Customers routinely submit phone numbers, email addresses, order tracking codes, and credit card "
        "digits in public verbatims. Storing or processing unredacted customer data violates EU GDPR Art. 9 and India DPDP 2023 statutory mandates.<br/>"
        "<b>4. The LLM Token Economics Trap:</b> Pumping 10,000 raw text reviews into commercial frontier LLMs (e.g., GPT-4o) costs $75–$150 per run "
        "and hits context window limits, while suffering severe attention degradation ('lost-in-the-middle') and hallucinated defect frequencies.",
        b.body_style
    ))
    story.append(Spacer(1, 4))

    # Analytical Comparison Table
    story.append(Paragraph("<b>Operational Triage Paradigms: Human vs. Naive LLM vs. InSight</b>", b.subsection_head))
    table_data = [
        [
            Paragraph("<b>Operational Dimension</b>", b.table_header),
            Paragraph("<b>Manual Analyst Triage</b>", b.table_header),
            Paragraph("<b>Naive Monolithic LLM</b>", b.table_header),
            Paragraph("<b>InSight Telemetry Codex</b>", b.table_header)
        ],
        [
            Paragraph("<b>10k Ingestion Latency</b>", b.tb_bold),
            Paragraph("330+ Human Hours (~4 weeks)", b.tb_style),
            Paragraph("15–30 min (API rate-limited)", b.tb_style),
            Paragraph("<b>&lt; 3.2 seconds</b> (ONNX vector batch)", b.tb_style)
        ],
        [
            Paragraph("<b>Cost per 10k Reviews</b>", b.tb_bold),
            Paragraph("$8,000 – $15,000 (Analyst salary)", b.tb_style),
            Paragraph("$85.00 – $150.00 (API tokens)", b.tb_style),
            Paragraph("<b>$0.0004</b> (Serverless CPU compute)", b.tb_style)
        ],
        [
            Paragraph("<b>Mixed Sentiment Handling</b>", b.tb_bold),
            Paragraph("High variance / subjective", b.tb_style),
            Paragraph("Blended rating / hallucination", b.tb_style),
            Paragraph("<b>Clause-level contrastive parsing</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Drift & Statistical Alerts</b>", b.tb_bold),
            Paragraph("None (Ad-hoc spreadsheets)", b.tb_style),
            Paragraph("None (Text output only)", b.tb_style),
            Paragraph("<b>PSI + Causal Relative Risk (RR)</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Enterprise BI Integration</b>", b.tb_bold),
            Paragraph("Manual CSV copy-paste", b.tb_style),
            Paragraph("Unstructured chat text", b.tb_style),
            Paragraph("<b>Live OData/REST Star Schema</b>", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(table_data, col_widths=[105, 125, 125, 132]))
    story.append(Spacer(1, 4))

    story.append(b.metric_banner([
        ("330 Hours → 3.2s", "Throughput Acceleration"),
        ("99.6% Reduction", "Processing Cost"),
        ("0% Data Leakage", "Strict Partitioning"),
        ("Full PII Redaction", "Pre-Vector Scrubbing")
    ]))

    return story
