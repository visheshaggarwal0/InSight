"""
Page 10: Chapter 7: Unsupervised Topic Discovery: UMAP & HDBSCAN
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)
from .charts import create_cluster_scatter_schematic

def build_page_10_ch7_clustering(b):
    story = []
    story.extend(b.page_header("CHAPTER 07: UNSUPERVISED TOPIC DISCOVERY", "UMAP MANIFOLD PROJECTION, HDBSCAN DENSITY CLUSTERING & ZERO-NOISE RECOVERY"))

    story.append(Paragraph(
        "Supervised classification models (e.g., fixed multiclass BERT classifiers) suffer an incurable flaw in review operations: "
        "they are blind to <i>emergent, zero-day defect modes</i>. If an enterprise releases a new product batch with a cracked silicone gasket, "
        "a supervised model trained on historical categories will misclassify the complaints as generic 'Quality' or 'Shipping'. "
        "InSight deploys an unsupervised pipeline combining <b>UMAP Riemannian manifold reduction</b> and <b>HDBSCAN density clustering</b>.",
        b.body_style
    ))

    story.append(b.callout(
        "THE ZERO-NOISE FALLBACK PROTOCOL",
        "Standard HDBSCAN discards sparse peripheral points into a cluster labeled <code>-1</code> ('Noise'). "
        "In production customer telemetry, discarding 20% to 35% of customer reviews as 'unassigned noise' is unacceptable to engineering leaders. "
        "InSight executes a <b>Nearest-Centroid Soft Assignment Fallback</b>: every outlier document is projected to its nearest cluster "
        "centroid in 384-d cosine space, ensuring 100% data coverage while logging a distance confidence metric."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Mathematical Formulation: c-TF-IDF Class-Based Representation</b>", b.section_head))
    story.append(Paragraph(
        "To generate descriptive, human-readable labels for discovered clusters without relying on hallucination-prone LLMs, "
        "InSight evaluates class-based term frequency-inverse document frequency (c-TF-IDF):<br/>"
        "<font name='Consolas'><b>W</b><sub>t, c</sub> = tf<sub>t, c</sub> &times; ln(1 + A / f<sub>t</sub>)</font><br/>"
        "where tf<sub>t, c</sub> is the frequency of word t inside cluster c, f<sub>t</sub> is the frequency of word t across all clusters, "
        "and A is the average number of words per cluster. This isolates terms uniquely overrepresented in that specific defect cluster "
        "(e.g., <i>'pump'</i>, <i>'leak'</i>, <i>'dispenser'</i>), creating instantly actionable topic headings.",
        b.body_style
    ))

    # UMAP Cluster Scatter Schematic Graphic
    story.append(create_cluster_scatter_schematic(width=b.pw, height=100))
    story.append(Spacer(1, 6))

    # Cluster Performance Table
    story.append(Paragraph("<b>Empirical Cluster Quality & Density Separation Metrics</b>", b.subsection_head))
    clust_data = [
        [
            Paragraph("<b>Cluster Parameter</b>", b.table_header),
            Paragraph("<b>Standard HDBSCAN</b>", b.table_header),
            Paragraph("<b>InSight Enhanced Pipeline</b>", b.table_header),
            Paragraph("<b>Business & Technical Impact</b>", b.table_header)
        ],
        [
            Paragraph("<b>Noise Data Ratio</b>", b.tb_bold),
            Paragraph("28.4% dropped (-1)", b.tb_style),
            Paragraph("<b>0.0% (Zero-Noise Fallback)</b>", b.tb_style),
            Paragraph("Full enterprise data auditability", b.tb_style)
        ],
        [
            Paragraph("<b>Topic Silhouette Score</b>", b.tb_bold),
            Paragraph("0.38 (High overlap)", b.tb_style),
            Paragraph("<b>0.54</b> (UMAP manifold space)", b.tb_style),
            Paragraph("Crisp separation between failure modes", b.tb_style)
        ],
        [
            Paragraph("<b>Labeling Determinism</b>", b.tb_bold),
            Paragraph("Stochastic LLM titles", b.tb_style),
            Paragraph("<b>Deterministic c-TF-IDF</b>", b.tb_style),
            Paragraph("Stable across re-index cycles", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(clust_data, col_widths=[115, 110, 130, 132]))

    return story
