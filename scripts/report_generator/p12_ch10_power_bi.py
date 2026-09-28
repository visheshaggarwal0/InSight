"""
Page 13: Chapter 10: Microsoft Power BI Corporate Analytics Bridge
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_13_ch10_power_bi(b):
    story = []
    story.extend(b.page_header("CHAPTER 10: MICROSOFT POWER BI BRIDGE", "STAR SCHEMA MODELING, LIVE ODATA/REST BRIDGE & PRE-BUILT DAX MEASURES"))

    story.append(Paragraph(
        "A common anti-pattern in enterprise engineering is attempting to reinvent corporate business intelligence dashboards "
        "inside custom React SPAs. Corporate finance, marketing, and executive leadership already rely on <b>Microsoft Power BI</b> "
        "for cross-departmental KPI consolidation, row-level security (RLS), and scheduled email subscriptions. "
        "InSight acts as the <b>AI Enrichment &amp; Cleansing Refinery</b>, streaming sanitized, structured telemetry into Power BI.",
        b.body_style
    ))

    story.append(b.callout(
        "THE DIVISION OF RESPONSIBILITY: INSIGHT VS. POWER BI",
        "<b>InSight's Mandate:</b> High-throughput ingestion, zero-trust PII scrubbing, contrastive clause parsing, ONNX embeddings, "
        "unsupervised UMAP clustering, and Platt calibrated risk scoring.<br/>"
        "<b>Power BI's Mandate:</b> Cross-filtering multidimensional pivot analysis, executive drill-downs, enterprise governance, "
        "and integration with Microsoft 365, Teams, and Azure Synapse."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>The InSight Star Schema Specification</b>", b.section_head))
    story.append(Paragraph(
        "The endpoint <font name='Consolas'>GET /api/export/powerbi</font> emits a normalized tabular payload designed for instant "
        "modeling into an enterprise Star Schema: a central fact table surrounded by four analytical dimensions.",
        b.body_style
    ))

    # Star Schema Specification Code Box
    schema_code = (
        "+-----------------------------------------------------------------------------------+\n"
        "|                        CENTRAL FACT: Fact_ReviewTelemetry                         |\n"
        "|  ReviewID (PK) | DateKey (FK) | ChannelKey (FK) | SKUKey (FK) | ClusterKey (FK)    |\n"
        "|  StarRating    | CalibratedSentiment (0-1)     | RelativeRiskScore                |\n"
        "|  PIIScrubbedFlag (T/F) | ChurnRiskFlag (T/F)   | ConcessiveMarkerFound (T/F)      |\n"
        "+-----------------------------------------+-----------------------------------------+\n"
        "       |                     |                     |                     |\n"
        "+------v------+       +------v------+       +------v------+       +------v------+\n"
        "| Dim_Channel |       |   Dim_SKU   |       | Dim_Cluster |       |  Dim_Date   |\n"
        "| Amazon, App |       | Serum, Gel, |       | Pump Seize, |       | Day, Week,  |\n"
        "| Store, Web  |       | SaaS Tier   |       | CSV Crash   |       | Month, Year |\n"
        "+-------------+       +-------------+       +-------------+       +-------------+"
    )
    story.append(b.code_box(schema_code, label="STAR SCHEMA TELEMETRY ARCHITECTURE"))
    story.append(Spacer(1, 4))

    # Pre-Built DAX Measures Table
    story.append(Paragraph("<b>Production DAX Formulations for Power BI Dashboards</b>", b.subsection_head))
    dax_data = [
        [
            Paragraph("<b>DAX Metric Name</b>", b.table_header),
            Paragraph("<b>DAX Expression Formulation</b>", b.table_header),
            Paragraph("<b>Executive Purpose</b>", b.table_header)
        ],
        [
            Paragraph("<b>Net Sentiment Score (NSS)</b>", b.tb_bold),
            Paragraph("<font name='Consolas'>DIVIDE(CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[CalibratedSentiment] &gt; 0.6) - CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[CalibratedSentiment] &lt; 0.4), COUNTROWS(Fact_ReviewTelemetry), 0) * 100</font>", b.tb_style),
            Paragraph("Primary board-level index of customer sentiment (+100 to -100).", b.tb_style)
        ],
        [
            Paragraph("<b>Concessive Defect Camouflage Rate</b>", b.tb_bold),
            Paragraph("<font name='Consolas'>DIVIDE(CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[ConcessiveMarkerFound] = TRUE(), Fact_ReviewTelemetry[StarRating] &gt;= 4), COUNTROWS(Fact_ReviewTelemetry), 0)</font>", b.tb_style),
            Paragraph("Measures percentage of positive star ratings concealing defects.", b.tb_style)
        ],
        [
            Paragraph("<b>High-Risk Churn Exposure</b>", b.tb_bold),
            Paragraph("<font name='Consolas'>CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[ChurnRiskFlag] = TRUE(), Fact_ReviewTelemetry[RelativeRiskScore] &gt; 2.5)</font>", b.tb_style),
            Paragraph("Quantifies total volume of customers facing P0 defect churn.", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(dax_data, col_widths=[125, 235, 127]))
    story.append(Spacer(1, 4))

    story.append(b.metric_banner([
        ("5-Minute Setup", "Power BI Web/OData Feed"),
        ("Live RLS Support", "Enterprise Azure Active Directory"),
        ("Auto-Refresh", "Scheduled Gateway Pipelines"),
        ("Zero Custom Code", "Standard Star Schema Ingestion")
    ]))

    return story
