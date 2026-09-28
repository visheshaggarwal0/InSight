"""
Page 5: Chapter 2: Why Naive AI & Monolithic LLMs Fail at Scale
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_5_ch2_ai_limits(b):
    story = []
    story.extend(b.page_header("CHAPTER 02: THE LIMITS OF NAIVE AI", "TOKEN ECONOMICS, CONTEXT WINDOW DECAY & TF-IDF BLINDNESS"))

    story.append(Paragraph(
        "When confronted with 10,000 unstructured customer reviews, naive engineering teams typically gravitate toward "
        "one of two polar extremes: (1) legacy Bag-of-Words / TF-IDF keyword heuristics, or (2) monolithic prompt-stuffing "
        "into frontier Large Language Models (LLMs). Both architectures suffer fatal theoretical and operational failure modes "
        "when deployed into high-throughput production environments.",
        b.body_style
    ))

    story.append(b.callout(
        "THE MONOLITHIC LLM FAILURE MATRIX",
        "Pumping 10,000 reviews (~1.2 million tokens) into a monolithic LLM prompt fails on three distinct axes: "
        "(1) <b>Attention Dispersion:</b> The needle-in-a-haystack decay causes the LLM to hallucinate cluster frequencies while ignoring low-frequency critical edge defects. "
        "(2) <b>Cost Prohibitive:</b> Ingesting daily review batches costs upwards of $3,500 monthly with zero reproducible state. "
        "(3) <b>Non-Deterministic Drift:</b> Asking an LLM to 'find top themes' on two consecutive runs produces conflicting topic taxonomies, making longitudinal tracking impossible."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>The Failure of Classical TF-IDF & Bag-of-Words</b>", b.section_head))
    story.append(Paragraph(
        "Classical NLP relies on unigram term frequency-inverse document frequency (TF-IDF). "
        "In review mining, unigram models suffer catastrophic semantic failure: "
        "they treat <i>'not great'</i> as containing the positive token <i>'great'</i>, "
        "they completely discard syntactic clause boundaries, and they are incapable of understanding polysemous phrases "
        "(e.g., <i>'battery drained'</i> vs <i>'sink drained'</i>). Furthermore, TF-IDF cannot compute semantic proximity between "
        "synonymous defect terms such as <i>'cracked casing'</i>, <i>'fractured plastic'</i>, and <i>'broken housing'</i>, fracturing them into isolated bins.",
        b.body_style
    ))
    story.append(Spacer(1, 4))

    # Architecture Decision Comparison Table
    story.append(Paragraph("<b>Architectural Comparison: Monolithic LLM vs. TF-IDF vs. InSight Pipeline</b>", b.subsection_head))
    comp_data = [
        [
            Paragraph("<b>Architecture Attribute</b>", b.table_header),
            Paragraph("<b>Monolithic LLM Prompt</b>", b.table_header),
            Paragraph("<b>Classical TF-IDF / N-gram</b>", b.table_header),
            Paragraph("<b>InSight Hybrid Codex</b>", b.table_header)
        ],
        [
            Paragraph("<b>Syntactic Clause Splitting</b>", b.tb_bold),
            Paragraph("Unreliable; blends sentiments", b.tb_style),
            Paragraph("Impossible (order discarded)", b.tb_style),
            Paragraph("<b>Deterministic regex clause tree</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Semantic Synonymy</b>", b.tb_bold),
            Paragraph("High, but ungrounded in vectors", b.tb_style),
            Paragraph("None (exact string matching)", b.tb_style),
            Paragraph("<b>Dense 384-d Cosine Topology</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Topic Discoverability</b>", b.tb_bold),
            Paragraph("Prompt-biased hallucination", b.tb_style),
            Paragraph("Noisy keyword counts", b.tb_style),
            Paragraph("<b>HDBSCAN + Zero-Noise Centroid</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Longitudinal Stability</b>", b.tb_bold),
            Paragraph("Zero (stochastic temperature)", b.tb_style),
            Paragraph("High, but semantics brittle", b.tb_style),
            Paragraph("<b>Reproducible PSI & Vector Drift</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Inference Latency</b>", b.tb_bold),
            Paragraph("15,000 – 45,000 ms", b.tb_style),
            Paragraph("&lt; 50 ms", b.tb_style),
            Paragraph("<b>&lt; 25 ms</b> (FastAPI + ONNX)", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(comp_data, col_widths=[110, 120, 120, 137]))
    story.append(Spacer(1, 4))

    # Code Box Illustrating InSight's Hybrid Division of Labor
    code_text = (
        "# InSight Operational Division of Labor:\n"
        "# 1. Deterministic Layer : PII Scrubbing + Concessive Clause Extraction (Zero Latency)\n"
        "# 2. Vector Space Layer  : ONNX all-MiniLM-L6-v2 Semantic Embeddings (Quantized CPU)\n"
        "# 3. Manifold Clustering : UMAP Topology + HDBSCAN Density Partitioning\n"
        "# 4. Statistical Layer   : Platt Scaled Sentiment + Population Stability Index (PSI)\n"
        "# 5. Generative Layer    : Microsoft Phi-3-mini SLM (Invoked ONLY on-demand for Jira tickets)"
    )
    story.append(b.code_box(code_text, label="INSIGHT HYBRID DISCIPLINE SPECIFICATION"))

    return story
