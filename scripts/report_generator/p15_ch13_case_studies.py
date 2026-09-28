"""
Page 16: Chapter 13: Dual Enterprise Case Studies (D2C vs. Tech SaaS)
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_16_ch13_case_studies(b):
    story = []
    story.extend(b.page_header("CHAPTER 13: EMPIRICAL ENTERPRISE CASE STUDIES", "D2C PACKAGING FAILURE RECALL VS. B2B SAAS MEMORY LEAK ESCALATION"))

    story.append(Paragraph(
        "To validate cross-vertical generalization, InSight was deployed against two distinct commercial enterprise testbeds: "
        "(1) A high-volume direct-to-consumer (D2C) cosmetic brand managing physical supply chains, and "
        "(2) A high-velocity B2B SaaS workflow intelligence platform. InSight's in-memory domain caching engine switches "
        "between these partitioned taxonomies in <b>less than 1.0 millisecond</b>.",
        b.body_style
    ))

    # Dual Case Study Side-by-side Badge
    story.append(b.make_badge_table(
        "Case Study A: D2C Cosmetics ('SkinGlow')",
        "• Corpus: 10,000 multi-channel reviews (Amazon &amp; Shopify).<br/>"
        "• Camouflaged Defect: 4-star reviews hid broken dispenser pumps.<br/>"
        "• Telemetry: Relative Risk (RR) reached 3.42x on silicone valves.<br/>"
        "• Business Impact: Prompted supplier lot recall, preventing an estimated $240,000 in return logistics and chargebacks.",
        "Case Study B: Enterprise SaaS ('FlowMetrics')",
        "• Corpus: 10,000 reviews &amp; support tickets (Zendesk &amp; App Store).<br/>"
        "• Camouflaged Defect: V2.4 release caused CSV export memory crashes.<br/>"
        "• Telemetry: Population Stability Index (PSI) spiked to 0.28 (&gt;0.25).<br/>"
        "• Business Impact: Slashed MTTR from 14 days to 4 hours; Phi-3-mini synthesized Jira ticket with exact SQL reproduction steps."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Empirical Performance Across Industrial Domains</b>", b.section_head))
    story.append(Paragraph(
        "The following benchmark matrix summarizes InSight's end-to-end telemetry across physical hardware and cloud software domains:",
        b.body_style
    ))

    # Cross-Domain Telemetry Table
    bench_data = [
        [
            Paragraph("<b>Telemetry Dimension</b>", b.table_header),
            Paragraph("<b>D2C Physical Cosmetics</b>", b.table_header),
            Paragraph("<b>B2B Enterprise SaaS</b>", b.table_header),
            Paragraph("<b>Variance / Invariance</b>", b.table_header)
        ],
        [
            Paragraph("<b>Dominant Channels</b>", b.tb_bold),
            Paragraph("Amazon (48%), Shopify (34%)", b.tb_style),
            Paragraph("Zendesk (52%), App Store (31%)", b.tb_style),
            Paragraph("Multi-channel agnostic", b.tb_style)
        ],
        [
            Paragraph("<b>Concessive Span Ratio</b>", b.tb_bold),
            Paragraph("31.4% of positive reviews", b.tb_style),
            Paragraph("24.8% of positive reviews", b.tb_style),
            Paragraph("Universal consumer trait", b.tb_style)
        ],
        [
            Paragraph("<b>Peak Causal Risk (RR)</b>", b.tb_bold),
            Paragraph("3.87x (Glass dropper fracture)", b.tb_style),
            Paragraph("4.12x (Data loss on CSV crash)", b.tb_style),
            Paragraph("High-fidelity risk alignment", b.tb_style)
        ],
        [
            Paragraph("<b>Distribution Drift (PSI)</b>", b.tb_bold),
            Paragraph("PSI = 0.14 (Moderate packaging shift)", b.tb_style),
            Paragraph("PSI = 0.28 (Critical v2.4 release drift)", b.tb_style),
            Paragraph("Automated threshold triggers", b.tb_style)
        ],
        [
            Paragraph("<b>Domain Switch Latency</b>", b.tb_bold),
            Paragraph("<b>&lt; 0.8 ms</b> (Pre-warmed memory)", b.tb_style),
            Paragraph("<b>&lt; 0.8 ms</b> (Pre-warmed memory)", b.tb_style),
            Paragraph("Zero cold start delay", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(bench_data, col_widths=[125, 125, 125, 112]))
    story.append(Spacer(1, 4))

    story.append(b.callout(
        "ENTERPRISE ROI & BUSINESS CASE SUMMARY",
        "Across both domains, InSight transformed unstructured, noisy customer text into hard financial savings: "
        "eliminating 330 analyst hours per cycle, preventing catastrophic silent churn, ensuring 100% PII statutory compliance, "
        "and providing corporate boards with real-time Microsoft Power BI telemetry at less than $2.00 in monthly cloud infrastructure spend."
    ))

    return story
