"""
InSight Technical Publication — Vector Graphics & Visual Charts
Publication-grade ReportLab vector drawings and architectural schematics.
"""

from reportlab.graphics.shapes import Drawing, Rect, String, Line, Group, Polygon, Circle
from reportlab.lib import colors

# Palette
c_emerald = colors.HexColor("#0F382E")
c_emerald_accent = colors.HexColor("#10B981")
c_emerald_light = colors.HexColor("#ECFDF5")
c_gold = colors.HexColor("#D97706")
c_gold_light = colors.HexColor("#FFFBEB")
c_slate_dark = colors.HexColor("#111827")
c_slate_body = colors.HexColor("#374151")
c_slate_muted = colors.HexColor("#6B7280")
c_border = colors.HexColor("#CBD5E1")
c_bg_card = colors.HexColor("#F8FAF8")
c_white = colors.HexColor("#FFFFFF")
c_danger = colors.HexColor("#EF4444")
c_danger_light = colors.HexColor("#FEF2F2")

F_SANS_BOLD = 'Helvetica-Bold'
F_SANS = 'Helvetica'
F_CODE = 'Courier'


def create_architecture_diagram(width=487, height=130):
    """
    Renders a publication-grade 3-tier architectural block schematic for Chapter 3.
    Properly disjoint vertical geometry: zero tier overlap, clear arrows, styled labels.
    """
    d = Drawing(width, height)
    
    # Outer Card Frame
    d.add(Rect(0, 0, width, height, rx=5, ry=5, fillColor=c_bg_card, strokeColor=c_border, strokeWidth=0.75))
    
    # Header label
    d.add(String(12, height - 13, "SYSTEM TOPOLOGY & DATA FLOW PIPELINE", fontName=F_SANS_BOLD, fontSize=7.5, fillColor=c_emerald))
    d.add(Line(12, height - 17, width - 12, height - 17, strokeColor=c_border, strokeWidth=0.5))

    # --- TIER 1: CLIENT PRESENTATION LAYER ---
    t1_y = height - 44
    t1_h = 22
    d.add(Rect(16, t1_y, width - 32, t1_h, rx=3, ry=3, fillColor=colors.HexColor("#F0FDF4"), strokeColor=c_emerald_accent, strokeWidth=1))
    d.add(String(24, t1_y + 13, "CLIENT LAYER (React 19 / TypeScript / Vite / Tailwind)", fontName=F_SANS_BOLD, fontSize=6.8, fillColor=c_emerald))
    d.add(String(24, t1_y + 4, "Executive Overview  |  Cluster Visualizer  |  Verbatim Drawer  |  Power BI OData Button", fontName=F_SANS, fontSize=5.8, fillColor=c_slate_body))
    
    # Connector Arrow Tier 1 -> Tier 2
    arr1_x = width / 2.0
    arr1_top = t1_y
    arr1_bot = t1_y - 12
    d.add(Line(arr1_x, arr1_top, arr1_x, arr1_bot, strokeColor=c_emerald_accent, strokeWidth=1.2))
    d.add(Polygon([arr1_x - 3, arr1_bot + 4, arr1_x + 3, arr1_bot + 4, arr1_x, arr1_bot], fillColor=c_emerald_accent, strokeColor=None))
    d.add(String(arr1_x + 6, arr1_bot + 3, "REST JSON API (Sub-25ms SLA)", fontName=F_SANS_BOLD, fontSize=5.5, fillColor=c_gold))

    # --- TIER 2: API & GATEWAY LAYER ---
    t2_y = arr1_bot - 22
    t2_h = 22
    d.add(Rect(16, t2_y, width - 32, t2_h, rx=3, ry=3, fillColor=colors.HexColor("#EFF6FF"), strokeColor=colors.HexColor("#3B82F6"), strokeWidth=1))
    d.add(String(24, t2_y + 13, "API GATEWAY LAYER (FastAPI / Uvicorn / Pydantic v2)", fontName=F_SANS_BOLD, fontSize=6.8, fillColor=colors.HexColor("#1E40AF")))
    d.add(String(24, t2_y + 4, "/overview  |  /clusters  |  /reviews  |  /generate_ticket  |  /export/powerbi", fontName=F_CODE, fontSize=5.8, fillColor=c_slate_dark))

    # Connector Arrow Tier 2 -> Tier 3
    arr2_x = width / 2.0
    arr2_top = t2_y
    arr2_bot = t2_y - 12
    d.add(Line(arr2_x, arr2_top, arr2_x, arr2_bot, strokeColor=colors.HexColor("#3B82F6"), strokeWidth=1.2))
    d.add(Polygon([arr2_x - 3, arr2_bot + 4, arr2_x + 3, arr2_bot + 4, arr2_x, arr2_bot], fillColor=colors.HexColor("#3B82F6"), strokeColor=None))
    d.add(String(arr2_x + 6, arr2_bot + 3, "In-Memory Pre-Warmed Domain Cache (< 1.0ms)", fontName=F_SANS_BOLD, fontSize=5.5, fillColor=c_emerald))

    # --- TIER 3: ML & TELEMETRY ENGINE (3 SUB-BOXES) ---
    t3_y = arr2_bot - 26
    t3_h = 26
    box_w = (width - 32 - 16) / 3.0

    # Box 3A: PII & Contrastive Parsing
    b1_x = 16
    d.add(Rect(b1_x, t3_y, box_w, t3_h, rx=3, ry=3, fillColor=colors.HexColor("#FEF3C7"), strokeColor=c_gold, strokeWidth=0.75))
    d.add(String(b1_x + 6, t3_y + 16, "INGRESS FIREWALL", fontName=F_SANS_BOLD, fontSize=6.2, fillColor=c_gold))
    d.add(String(b1_x + 6, t3_y + 8, "Regex + Luhn Card Check", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_dark))
    d.add(String(b1_x + 6, t3_y + 2, "Contrastive Clause Splitting", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_dark))

    # Box 3B: ONNX Vector Space & Clustering
    b2_x = b1_x + box_w + 8
    d.add(Rect(b2_x, t3_y, box_w, t3_h, rx=3, ry=3, fillColor=colors.HexColor("#ECFDF5"), strokeColor=c_emerald, strokeWidth=0.75))
    d.add(String(b2_x + 6, t3_y + 16, "VECTOR SPACE ENGINE", fontName=F_SANS_BOLD, fontSize=6.2, fillColor=c_emerald))
    d.add(String(b2_x + 6, t3_y + 8, "ONNX MiniLM 384-d Embeddings", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_dark))
    d.add(String(b2_x + 6, t3_y + 2, "UMAP + HDBSCAN + Zero-Noise", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_dark))

    # Box 3C: Statistical Governance & SLM
    b3_x = b2_x + box_w + 8
    d.add(Rect(b3_x, t3_y, box_w, t3_h, rx=3, ry=3, fillColor=colors.HexColor("#F3F4F6"), strokeColor=colors.HexColor("#6B7280"), strokeWidth=0.75))
    d.add(String(b3_x + 6, t3_y + 16, "TELEMETRY & REMEDIATION", fontName=F_SANS_BOLD, fontSize=6.2, fillColor=c_slate_dark))
    d.add(String(b3_x + 6, t3_y + 8, "Platt Scaling & PSI Drift Alert", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_dark))
    d.add(String(b3_x + 6, t3_y + 2, "Phi-3-mini Jira Bug Tickets", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_dark))

    return d


def create_latency_bar_chart(width=487, height=105):
    """
    Renders an executive horizontal bar chart comparing PyTorch vs ONNX vs In-Memory Cache.
    For Chapter 6: Microsoft ONNX Runtime.
    """
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, rx=5, ry=5, fillColor=c_bg_card, strokeColor=c_border, strokeWidth=0.75))
    d.add(String(12, height - 14, "INFERENCE LATENCY COMPARISON (COMMODITY SERVERLESS CPU, LOWER IS BETTER)", fontName=F_SANS_BOLD, fontSize=7.2, fillColor=c_emerald))
    d.add(Line(12, height - 18, width - 12, height - 18, strokeColor=c_border, strokeWidth=0.5))

    x_start = 145
    max_w = width - x_start - 85
    y_base = 14
    row_h = 24

    # Row 1: PyTorch
    y1 = y_base + 2 * row_h
    d.add(String(14, y1 + 5, "Standard PyTorch v2.3", fontName=F_SANS_BOLD, fontSize=6.8, fillColor=c_slate_dark))
    d.add(String(14, y1 - 3, "Python GIL / Heavy Container", fontName=F_SANS, fontSize=5.8, fillColor=c_slate_muted))
    d.add(Rect(x_start, y1 - 2, max_w, 14, rx=2, ry=2, fillColor=colors.HexColor("#94A3B8"), strokeColor=None))
    d.add(String(x_start + max_w + 6, y1 + 2, "34.8 ms / item", fontName=F_SANS_BOLD, fontSize=6.5, fillColor=c_slate_dark))

    # Row 2: Microsoft ONNX Runtime
    y2 = y_base + 1 * row_h
    w2 = max_w * (3.8 / 34.8)
    d.add(String(14, y2 + 5, "Microsoft ONNX Runtime", fontName=F_SANS_BOLD, fontSize=6.8, fillColor=c_emerald))
    d.add(String(14, y2 - 3, "Native C++ AVX-512 Kernels", fontName=F_SANS, fontSize=5.8, fillColor=c_emerald_accent))
    d.add(Rect(x_start, y2 - 2, w2, 14, rx=2, ry=2, fillColor=c_emerald_accent, strokeColor=None))
    d.add(String(x_start + w2 + 6, y2 + 2, "3.8 ms (9.2x Speedup)", fontName=F_SANS_BOLD, fontSize=6.5, fillColor=c_emerald))

    # Row 3: InSight Domain Cache Hit
    y3 = y_base
    w3 = max_w * 0.02
    d.add(String(14, y3 + 5, "InSight DOMAIN_CACHE", fontName=F_SANS_BOLD, fontSize=6.8, fillColor=c_gold))
    d.add(String(14, y3 - 3, "Pre-warmed in-memory dict", fontName=F_SANS, fontSize=5.8, fillColor=c_slate_muted))
    d.add(Rect(x_start, y3 - 2, w3, 14, rx=2, ry=2, fillColor=c_gold, strokeColor=None))
    d.add(String(x_start + w3 + 6, y3 + 2, "< 0.01 ms (Instantaneous)", fontName=F_SANS_BOLD, fontSize=6.5, fillColor=c_gold))

    return d


def create_model_performance_chart(width=487, height=105):
    """
    Renders grouped bar chart for Chapter 9: Model Governance.
    Shortened title to avoid legend collision.
    """
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, rx=5, ry=5, fillColor=c_bg_card, strokeColor=c_border, strokeWidth=0.75))
    d.add(String(12, height - 14, "DISJOINT GROUND TRUTH EVALUATION (1,000 SAMPLES, ACCURACY = 83.4%)", fontName=F_SANS_BOLD, fontSize=6.8, fillColor=c_emerald))
    d.add(Line(12, height - 18, width - 12, height - 18, strokeColor=c_border, strokeWidth=0.5))

    # Legend
    leg_y = height - 14
    d.add(Rect(width - 150, leg_y - 2, 7, 7, rx=1, ry=1, fillColor=c_emerald, strokeColor=None))
    d.add(String(width - 139, leg_y, "Precision", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_body))
    d.add(Rect(width - 100, leg_y - 2, 7, 7, rx=1, ry=1, fillColor=c_emerald_accent, strokeColor=None))
    d.add(String(width - 89, leg_y, "Recall", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_body))
    d.add(Rect(width - 52, leg_y - 2, 7, 7, rx=1, ry=1, fillColor=c_gold, strokeColor=None))
    d.add(String(width - 41, leg_y, "F1-Score", fontName=F_SANS, fontSize=5.5, fillColor=c_slate_body))

    # 3 Groups: Negative, Neutral, Positive
    groups = [
        ("Negative Class (Defects)", [0.874, 0.842, 0.858]),
        ("Neutral Class", [0.770, 0.790, 0.780]),
        ("Positive Class", [0.854, 0.863, 0.858]),
    ]

    group_w = (width - 40) / 3.0
    bar_w = 18
    max_h = 48
    y_base = 24

    for i, (label, vals) in enumerate(groups):
        gx = 24 + i * group_w
        d.add(String(gx + 30, y_base - 10, label, fontName=F_SANS_BOLD, fontSize=6.2, fillColor=c_slate_dark, textAnchor='middle'))

        # Precision
        h_p = vals[0] * max_h
        d.add(Rect(gx + 5, y_base, bar_w, h_p, rx=2, ry=2, fillColor=c_emerald, strokeColor=None))
        d.add(String(gx + 5 + bar_w/2.0, y_base + h_p + 3, f"{vals[0]*100:.1f}%", fontName=F_SANS, fontSize=5.0, fillColor=c_slate_dark, textAnchor='middle'))

        # Recall
        h_r = vals[1] * max_h
        d.add(Rect(gx + 5 + bar_w + 3, y_base, bar_w, h_r, rx=2, ry=2, fillColor=c_emerald_accent, strokeColor=None))
        d.add(String(gx + 5 + bar_w + 3 + bar_w/2.0, y_base + h_r + 3, f"{vals[1]*100:.1f}%", fontName=F_SANS, fontSize=5.0, fillColor=c_slate_dark, textAnchor='middle'))

        # F1
        h_f = vals[2] * max_h
        d.add(Rect(gx + 5 + (bar_w + 3)*2, y_base, bar_w, h_f, rx=2, ry=2, fillColor=c_gold, strokeColor=None))
        d.add(String(gx + 5 + (bar_w + 3)*2 + bar_w/2.0, y_base + h_f + 3, f"{vals[2]*100:.1f}%", fontName=F_SANS, fontSize=5.0, fillColor=c_slate_dark, textAnchor='middle'))

    return d


def create_causal_risk_bar_chart(width=487, height=105):
    """
    Renders horizontal bar chart for Chapter 8: Causal Relative Risk (RR).
    Shows how defect categories compare to the P0 alert threshold of RR=2.5.
    """
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, rx=5, ry=5, fillColor=c_bg_card, strokeColor=c_border, strokeWidth=0.75))
    d.add(String(12, height - 14, "CAUSAL RELATIVE RISK (RR) VS. CHURN HAZARD (ALERT THRESHOLD: RR > 2.50x)", fontName=F_SANS_BOLD, fontSize=7.0, fillColor=c_emerald))
    d.add(Line(12, height - 18, width - 12, height - 18, strokeColor=c_border, strokeWidth=0.5))

    x_start = 145
    max_w = width - x_start - 75
    row_h = 24
    y_base = 14

    items = [
        ("Glass Dropper Fracture", 3.87, c_danger, "3.87x (P0 Safety Recall)"),
        ("Pump Seizure / Jam", 3.42, c_danger, "3.42x (P0 Critical Bug)"),
        ("Scent / Fragrance Level", 0.82, colors.HexColor("#94A3B8"), "0.82x (Neutral / P3 Backlog)")
    ]

    # Draw vertical threshold line at RR = 2.5 (scale: 0 to 4.5)
    thresh_x = x_start + (2.5 / 4.5) * max_w
    d.add(Line(thresh_x, 10, thresh_x, height - 22, strokeColor=c_danger, strokeWidth=1, strokeDashArray=[2, 2]))
    d.add(String(thresh_x, height - 28, "P0 Alert Line (2.5x)", fontName=F_SANS_BOLD, fontSize=5.2, fillColor=c_danger, textAnchor='middle'))

    for i, (title, rr, bar_color, tag) in enumerate(items):
        y = y_base + (2 - i) * row_h
        d.add(String(14, y + 4, title, fontName=F_SANS_BOLD, fontSize=6.5, fillColor=c_slate_dark))
        bar_len = (rr / 4.5) * max_w
        d.add(Rect(x_start, y - 2, bar_len, 13, rx=2, ry=2, fillColor=bar_color, strokeColor=None))
        d.add(String(x_start + bar_len + 6, y + 2, tag, fontName=F_SANS_BOLD, fontSize=6.0, fillColor=bar_color))

    return d


def create_cluster_scatter_schematic(width=487, height=105):
    """
    Renders 2D UMAP Manifold & Zero-Noise Fallback schematic for Chapter 7.
    Shows 3 dense clusters + soft centroid assignment for unclustered outliers.
    """
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, rx=5, ry=5, fillColor=c_bg_card, strokeColor=c_border, strokeWidth=0.75))
    d.add(String(12, height - 14, "UMAP 2D MANIFOLD TOPOLOGY & ZERO-NOISE RECOVERY SCHEMATIC", fontName=F_SANS_BOLD, fontSize=7.0, fillColor=c_emerald))
    d.add(Line(12, height - 18, width - 12, height - 18, strokeColor=c_border, strokeWidth=0.5))

    # Cluster 1: Formula Quality (Emerald)
    c1_x, c1_y = 110, 48
    d.add(Circle(c1_x, c1_y, 24, fillColor=colors.HexColor("#D1FAE5"), strokeColor=c_emerald_accent, strokeWidth=0.75))
    d.add(Circle(c1_x, c1_y, 3.5, fillColor=c_emerald, strokeColor=None))
    d.add(String(c1_x, c1_y - 32, "Cluster 0: Formula Praise", fontName=F_SANS_BOLD, fontSize=5.8, fillColor=c_emerald, textAnchor='middle'))
    d.add(String(c1_x, c1_y - 39, "N = 4,210 reviews", fontName=F_SANS, fontSize=5.0, fillColor=c_slate_muted, textAnchor='middle'))

    # Cluster 2: Dispenser Jam (Gold/Red)
    c2_x, c2_y = 260, 56
    d.add(Circle(c2_x, c2_y, 20, fillColor=colors.HexColor("#FEF3C7"), strokeColor=c_gold, strokeWidth=0.75))
    d.add(Circle(c2_x, c2_y, 3.5, fillColor=c_gold, strokeColor=None))
    d.add(String(c2_x, c2_y - 28, "Cluster 1: Pump Seizure", fontName=F_SANS_BOLD, fontSize=5.8, fillColor=c_gold, textAnchor='middle'))
    d.add(String(c2_x, c2_y - 35, "N = 820 (P0 Critical)", fontName=F_SANS, fontSize=5.0, fillColor=c_danger, textAnchor='middle'))

    # Cluster 3: Glass Fractures (Danger Red)
    c3_x, c3_y = 400, 44
    d.add(Circle(c3_x, c3_y, 18, fillColor=colors.HexColor("#FEE2E2"), strokeColor=c_danger, strokeWidth=0.75))
    d.add(Circle(c3_x, c3_y, 3.5, fillColor=c_danger, strokeColor=None))
    d.add(String(c3_x, c3_y - 26, "Cluster 2: Dropper Fracture", fontName=F_SANS_BOLD, fontSize=5.8, fillColor=c_danger, textAnchor='middle'))
    d.add(String(c3_x, c3_y - 33, "N = 410 (P0 Safety)", fontName=F_SANS, fontSize=5.0, fillColor=c_danger, textAnchor='middle'))

    # Outlier Point (formerly Noise -1) rescued via Centroid Fallback
    ox, oy = 330, 22
    d.add(Circle(ox, oy, 2.5, fillColor=colors.HexColor("#6B7280"), strokeColor=None))
    d.add(Line(ox, oy, c2_x, c2_y, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=0.75, strokeDashArray=[2, 2]))
    d.add(String(ox, oy - 9, "Soft-Assigned Outlier to Cluster 1", fontName=F_SANS_BOLD, fontSize=5.0, fillColor=colors.HexColor("#4B5563"), textAnchor='middle'))

    return d
