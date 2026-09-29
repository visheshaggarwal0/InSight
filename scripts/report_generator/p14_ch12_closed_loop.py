"""
Page 15: Chapter 12: Closed-Loop Remediation: SLM Incident Generation
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_15_ch12_closed_loop(b):
    story = []
    story.extend(b.page_header("CHAPTER 12: CLOSED-LOOP REMEDIATION", "MICROSOFT PHI-3-MINI SLM, ON-DEMAND JIRA TICKET SYNTHESIS & HUMAN-IN-THE-LOOP TRIAGE"))

    story.append(Paragraph(
        "A chronic flaw in modern text analytics platforms is <i>passive observation</i>: systems generate colorful dashboards "
        "and word clouds, but leave the translation of insights into concrete engineering action entirely to human memory. "
        "An unresolved defect continues to churn customers while reports languish in executive email inboxes. "
        "InSight bridges the gap between customer complaints and engineering sprints via <b>Closed-Loop SLM Remediation</b>.",
        b.body_style
    ))

    story.append(b.callout(
        "THE ON-DEMAND SLM INVOCATION DISCIPLINE",
        "Rather than running expensive continuous generative LLMs over all 10,000 incoming reviews, InSight invokes "
        "<b>Microsoft Phi-3-mini</b> (3.8B parameter Small Language Model) <i>strictly on-demand</i> when an authorized reliability "
        "engineer clicks 'Generate Jira Incident' on an identified defect cluster. This eliminates 99.8% of generative token waste "
        "while ensuring 100% human-in-the-loop oversight prior to Jira ticket synchronization."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Structured Jira Defect Ticket Architecture</b>", b.section_head))
    story.append(Paragraph(
        "When invoked, the Phi-3-mini model ingests the cluster's c-TF-IDF keyword vector, its top contrastive complaint spans, "
        "and its empirical Relative Risk (RR) score. It emits an industry-standard Jira defect ticket adhering to strict markdown formatting:",
        b.body_style
    ))

    # Jira Ticket Markdown Output Code Box
    jira_sample = (
        "### [DEFECT-P0] Cosmetic Pump Vacuum Failure & Dropper Fractures\n"
        "**Severity:** P0 - Blocker | **Causal Relative Risk (RR):** 3.42x | **Affected Cohort:** Batch 2024-Q3\n"
        "**Discovered Via:** InSight Cluster #2 (Dispenser Seizure / Seal Defect)\n\n"
        "#### 1. Executive Summary & Root-Cause Hypothesis\n"
        "Customer verbatims indicate that the silicone vacuum seal inside the 30ml dropper assembly undergoes "
        "viscosity crystallization upon exposure to ambient air, causing complete pump seizure after 3 to 5 applications.\n\n"
        "#### 2. Representative Customer Verbatim Evidence (Scrubbed)\n"
        "- *'Formula is sublime, **but the pump mechanism broke on day three** and won't dispense.'* [Amazon, 4-Star]\n"
        "- *'Love the glow, **however the glass dropper cracked inside the bottle**.'* [Shopify, 3-Star]\n\n"
        "#### 3. Recommended Remediation & QA Action Items\n"
        "- [ ] Quarantine Supplier Lot #SL-9941 (Silicone Dispenser Valves).\n"
        "- [ ] Issue proactive customer replacement units to affected Shopify cohort."
    )
    story.append(b.code_box(jira_sample, label="SYNTHESIZED PHI-3-MINI JIRA DEFECT REPORT"))
    story.append(Spacer(1, 4))

    # Comparison Table: Passive Dashboard vs InSight Closed Loop
    story.append(Paragraph("<b>Remediation Workflow Comparison: Passive vs. Closed Loop</b>", b.subsection_head))
    loop_data = [
        [
            Paragraph("<b>Workflow Phase</b>", b.table_header),
            Paragraph("<b>Traditional Passive Dashboard</b>", b.table_header),
            Paragraph("<b>InSight Closed-Loop Engineering</b>", b.table_header)
        ],
        [
            Paragraph("<b>Defect Identification</b>", b.tb_bold),
            Paragraph("Manual scanning of word clouds", b.tb_style),
            Paragraph("<b>Automated UMAP centroid &amp; Relative Risk alert</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Evidence Gathering</b>", b.tb_bold),
            Paragraph("Analyst reads 100+ raw verbatims", b.tb_style),
            Paragraph("<b>Contrastive clause extraction with string offsets</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Ticket Authoring</b>", b.tb_bold),
            Paragraph("30–60 minutes human writing", b.tb_style),
            Paragraph("<b>&lt; 850 ms automated Phi-3-mini Markdown generation</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Mean Time to Remediation (MTTR)</b>", b.tb_bold),
            Paragraph("14 to 28 days", b.tb_style),
            Paragraph("<b>&lt; 4 hours</b> (Same-day engineering triage)", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(loop_data, col_widths=[140, 170, 177]))

    return story
