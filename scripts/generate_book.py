"""
InSight — The Canonical System Architecture & Engineering Monograph
Comprehensive 17-Page Editorial Publication for Microsoft Innovate 2026 (Problem Statement 17).
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageBreak

# Add repository root and local directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from report_generator.styles import StylesBundle, NumberedCanvas, REPO_ROOT
from report_generator.p01_cover import build_page_1_cover
from report_generator.p02_toc import build_page_2_toc_part1, build_page_3_toc_part2
from report_generator.p03_ch1_crisis import build_page_4_ch1_crisis
from report_generator.p04_ch2_ai_limits import build_page_5_ch2_ai_limits
from report_generator.p05_ch3_architecture import build_page_6_ch3_architecture
from report_generator.p06_ch4_pii import build_page_7_ch4_pii
from report_generator.p07_ch5_clause_parsing import build_page_8_ch5_clause_parsing
from report_generator.p08_ch6_onnx_embeddings import build_page_9_ch6_onnx_embeddings
from report_generator.p09_ch7_clustering import build_page_10_ch7_clustering
from report_generator.p10_ch8_drift_monitoring import build_page_11_ch8_drift_monitoring
from report_generator.p11_ch9_model_governance import build_page_12_ch9_model_governance
from report_generator.p12_ch10_power_bi import build_page_13_ch10_power_bi
from report_generator.p13_ch11_azure_cloud import build_page_14_ch11_azure_cloud
from report_generator.p14_ch12_closed_loop import build_page_15_ch12_closed_loop
from report_generator.p15_ch13_case_studies import build_page_16_ch13_case_studies
from report_generator.p16_ch14_appendix import build_page_17_ch14_appendix


def generate_insight_book(filename="InSight_Technical_Publication.pdf"):
    """
    Assembles all editorial pages of the InSight Technical Monograph and compiles the final PDF.
    """
    output_path = os.path.join(repo_root, filename) if not os.path.isabs(filename) else filename

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=48,
        bottomMargin=50,
    )

    b = StylesBundle(printable_width=487.27)
    story = []

    pages = [
        ("Cover Page", build_page_1_cover),
        ("Table of Contents (Part I)", build_page_2_toc_part1),
        ("Table of Contents (Part II)", build_page_3_toc_part2),
        ("Chapter 01: The 10,000 Reviews Deluge", build_page_4_ch1_crisis),
        ("Chapter 02: Why Naive AI & Monolithic LLMs Fail", build_page_5_ch2_ai_limits),
        ("Chapter 03: System Topology & Dual Personas", build_page_6_ch3_architecture),
        ("Chapter 04: Zero-Trust PII Sanitization", build_page_7_ch4_pii),
        ("Chapter 05: Contrastive Clause Parsing", build_page_8_ch5_clause_parsing),
        ("Chapter 06: ONNX Dense Vector Projection", build_page_9_ch6_onnx_embeddings),
        ("Chapter 07: Unsupervised Topic Discovery", build_page_10_ch7_clustering),
        ("Chapter 08: Statistical Telemetry & Drift", build_page_11_ch8_drift_monitoring),
        ("Chapter 09: Model Governance & Calibration", build_page_12_ch9_model_governance),
        ("Chapter 10: Microsoft Power BI Bridge", build_page_13_ch10_power_bi),
        ("Chapter 11: Azure Serverless Topology", build_page_14_ch11_azure_cloud),
        ("Chapter 12: Closed-Loop Remediation", build_page_15_ch12_closed_loop),
        ("Chapter 13: Empirical Enterprise Case Studies", build_page_16_ch13_case_studies),
        ("Chapter 14: Architectural Decision Records & Sign-Off", build_page_17_ch14_appendix),
    ]

    print(f"[INFO] Initializing InSight Book Assembly with {len(pages)} canonical pages...")

    for i, (name, builder_fn) in enumerate(pages):
        page_flowables = builder_fn(b)
        story.extend(page_flowables)
        if i < len(pages) - 1:
            story.append(PageBreak())

    print(f"[INFO] Building PDF document: {output_path}...")
    doc.build(story, canvasmaker=NumberedCanvas)
    
    file_size_kb = os.path.getsize(output_path) / 1024.0
    print(f"[SUCCESS] InSight Technical Monograph compiled successfully!")
    print(f"          Path: {output_path}")
    print(f"          Size: {file_size_kb:.1f} KB")
    print(f"          Total Pages: {len(pages)}")


if __name__ == "__main__":
    generate_insight_book()
