"""
Page 11: Chapter 8: Statistical Telemetry: PSI & Causal Relative Risk
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

from .charts import create_causal_risk_bar_chart

def build_page_11_ch8_drift_monitoring(b):
    story = []
    story.extend(b.page_header("CHAPTER 08: STATISTICAL TELEMETRY & DRIFT", "POPULATION STABILITY INDEX (PSI), EPIDEMIOLOGICAL RELATIVE RISK & CAUSAL ATTRIBUTION"))

    story.append(Paragraph(
        "Modern consumer platforms cannot rely solely on static review counts. A sudden surge in complaints could reflect "
        "either a catastrophic manufacturing defect or simply an aggressive holiday marketing campaign driving 5x traffic. "
        "To distinguish between harmless volume growth and severe structural failure, InSight incorporates "
        "<b>Population Stability Index (PSI)</b> monitoring and <b>Causal Relative Risk (RR)</b> analysis.",
        b.body_style
    ))

    story.append(b.callout(
        "THE VOLUME BIAS TRAP IN CUSTOMER SUCCESS",
        "Raw complaint volume is a notoriously deceptive indicator. A cosmetic product may have 300 minor complaints regarding 'fragrance scent' "
        "which produces a negligible 2% churn rate, while having only 35 complaints regarding 'bottle pump seizure' that produces an "
        "85% customer churn rate. Prioritizing by raw count wastes engineering capital on cosmetic tweaks while existential defects fester."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Population Stability Index (PSI) Formulation</b>", b.section_head))
    story.append(Paragraph(
        "PSI quantifies the degree of divergence between a baseline reference population distribution P (e.g., Q1 historical reviews) "
        "and an empirical target observation window Q (e.g., current production week across B sentiment/topic bins):<br/>"
        "<font name='Consolas'><b>PSI</b> = &Sigma; (Q<sub>b</sub> - P<sub>b</sub>) &times; ln(Q<sub>b</sub> / P<sub>b</sub>)</font><br/>"
        "InSight utilizes standard statistical governance thresholds: "
        "PSI &lt; 0.10 indicates demographic stability; 0.10 &le; PSI &le; 0.25 flags moderate shift requiring review; "
        "and PSI &gt; 0.25 indicates significant structural drift, triggering automated Slack/Jira escalation warnings.",
        b.body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Causal Relative Risk (RR) Formulation</b>", b.section_head))
    story.append(Paragraph(
        "Borrowing from biostatistical epidemiology, InSight measures the causal impact of a specific product defect on customer churn risk. "
        "Constructing a 2 &times; 2 contingency table of customers exposed to defect D versus unexposed customers: "
        "<br/><font name='Consolas'><b>Relative Risk (RR)</b> = P(Churn | D) / P(Churn | &not;D) = [a / (a + b)] / [c / (c + d)]</font><br/>"
        "where a is defect-exposed churners, b is defect-exposed retainers, c is unexposed churners, and d is unexposed retainers. "
        "An RR &gt; 2.5 proves that encountering the defect increases customer abandonment odds by 150%, justifying immediate P0 priority.",
        b.body_style
    ))
    story.append(Spacer(1, 4))

    # Vector Causal Risk Bar Chart
    story.append(create_causal_risk_bar_chart(width=b.pw, height=90))
    story.append(Spacer(1, 5))

    # Contingency & Metric Table
    story.append(Paragraph("<b>Empirical Defect Attribution Matrix (D2C Cosmetics Corpus)</b>", b.subsection_head))
    rr_data = [
        [
            Paragraph("<b>Identified Failure Mode</b>", b.table_header),
            Paragraph("<b>Raw Volume</b>", b.table_header),
            Paragraph("<b>Exposed Churn Rate</b>", b.table_header),
            Paragraph("<b>Relative Risk (RR)</b>", b.table_header),
            Paragraph("<b>Action Priority</b>", b.table_header)
        ],
        [
            Paragraph("<b>Pump Seizure / Dispenser Jam</b>", b.tb_bold),
            Paragraph("82 reviews", b.tb_style),
            Paragraph("78.4%", b.tb_style),
            Paragraph("<b>3.42x</b> (p &lt; 0.001)", b.tb_style),
            Paragraph("<font color='#EF4444'><b>P0 Critical (Immediate)</b></font>", b.tb_style)
        ],
        [
            Paragraph("<b>Glass Dropper Hairline Fracture</b>", b.tb_bold),
            Paragraph("41 reviews", b.tb_style),
            Paragraph("85.1%", b.tb_style),
            Paragraph("<b>3.87x</b> (p &lt; 0.001)", b.tb_style),
            Paragraph("<font color='#EF4444'><b>P0 Safety Recall</b></font>", b.tb_style)
        ],
        [
            Paragraph("<b>Scent / Fragrance Intensity</b>", b.tb_bold),
            Paragraph("310 reviews", b.tb_style),
            Paragraph("11.2%", b.tb_style),
            Paragraph("<b>0.82x</b> (Neutral)", b.tb_style),
            Paragraph("<font color='#6B7280'>P3 Backlog / Low</font>", b.tb_style)
        ]
    ]
    story.append(b.booktabs_table(rr_data, col_widths=[140, 70, 95, 95, 87], pad=2.8))
    story.append(Spacer(1, 5))

    # Metric Banner
    story.append(b.metric_banner([
        ("PSI &lt; 0.10", "Baseline Stability"),
        ("RR = 3.87x", "Peak Churn Exposure"),
        ("Bayesian Smoothing", "Zero-Division Guard"),
        ("Automated Alerts", "P0 / P1 Webhooks")
    ]))

    return story
