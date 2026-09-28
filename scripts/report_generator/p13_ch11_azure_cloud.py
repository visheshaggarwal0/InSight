"""
Page 14: Chapter 11: Enterprise Azure Serverless Deployment
"""
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    F_TITLE, F_SANS_BOLD, F_SANS, F_BODY, F_BODY_BOLD,
    c_emerald, c_gold, c_slate_dark, c_slate_muted, c_white, c_border
)

def build_page_14_ch11_azure_cloud(b):
    story = []
    story.extend(b.page_header("CHAPTER 11: AZURE SERVERLESS TOPOLOGY", "AZURE STATIC WEB APPS, CONTAINER APPS CONSUMPTION, SCALE-TO-ZERO & $50 BUDGET GOVERNANCE"))

    story.append(Paragraph(
        "Deploying AI systems to enterprise cloud environments often triggers severe financial leakage: always-on VM instances "
        "(e.g., standard GPU virtual machines or dedicated App Service Plans) bill hundreds of dollars monthly even when completely "
        "idle. For the Microsoft Innovate evaluation environment, InSight implements an <b>Azure Serverless Architecture</b> "
        "engineered for enterprise resilience and rigorous cost control, operating comfortably under a strict <b>$50 budget limit</b>.",
        b.body_style
    ))

    story.append(b.callout(
        "THE SCALE-TO-ZERO FINANCIAL GOVERNANCE PROTOCOL",
        "By binding the FastAPI backend to Azure Container Apps (ACA) on the Consumption Plan with <code>min-replicas = 0</code>, "
        "the compute infrastructure terminates completely during idle windows. The platform charges <b>$0.00 per hour</b> when no "
        "requests are actively executing, while warming up in under 1.8 seconds on inbound API requests. "
        "Projected evaluation spend is <b>less than $2.00 per month</b>."
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>The Dual-Tier Azure Serverless Topology</b>", b.section_head))
    story.append(Paragraph(
        "<b>1. Azure Static Web Apps (Free Tier):</b> Hosts the compiled React 19 single-page application. Features native global "
        "Microsoft edge CDN caching, automatic SSL certificate provisioning, and direct GitHub Actions CI/CD workflows on push.<br/>"
        "<b>2. Azure Container Apps (ACA) & Container Registry (ACR):</b> Hosts the containerized FastAPI backend. Configured with "
        "0.5 vCPU and 1.0 GiB RAM per replica. Benefits from Azure's free monthly grant of 180,000 vCPU-seconds and 360,000 GiB-seconds.<br/>"
        "<b>3. Azure Cost Management Hard Budget Alert:</b> Configured at <b>$20.00 (40% of credit)</b> to prevent unintended financial drain.",
        b.body_style
    ))

    # Azure Infrastructure Cost Table
    story.append(Paragraph("<b>Azure Cloud Architecture Cost Breakdown & Free Tier Allowance</b>", b.subsection_head))
    cost_data = [
        [
            Paragraph("<b>Azure Service Resource</b>", b.table_header),
            Paragraph("<b>Tier / Configuration</b>", b.table_header),
            Paragraph("<b>Monthly Free Allowance</b>", b.table_header),
            Paragraph("<b>Estimated Monthly Spend</b>", b.table_header)
        ],
        [
            Paragraph("<b>Azure Static Web Apps</b>", b.tb_bold),
            Paragraph("Free Tier (Edge CDN)", b.tb_style),
            Paragraph("100 GB Bandwidth / Month", b.tb_style),
            Paragraph("<b>$0.00 / month</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Azure Container Apps</b>", b.tb_bold),
            Paragraph("Consumption (0.5 vCPU, 1 GB)", b.tb_style),
            Paragraph("180k vCPU-s, 360k GiB-s free", b.tb_style),
            Paragraph("<b>$0.00 – $1.20 / month</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Azure Container Registry</b>", b.tb_bold),
            Paragraph("Basic Tier (10 GB storage)", b.tb_style),
            Paragraph("Included within trial credits", b.tb_style),
            Paragraph("<b>$0.167 / day (~$0.80 for eval)</b>", b.tb_style)
        ],
        [
            Paragraph("<b>Total Solution Spend</b>", b.tb_bold),
            Paragraph("Full Production Deployment", b.tb_style),
            Paragraph("Scale-to-Zero Active", b.tb_style),
            Paragraph("<b>&lt; $2.00 / Month (96% buffer)</b>", b.tb_style)
        ]
    ]

    story.append(b.booktabs_table(cost_data, col_widths=[125, 125, 125, 112]))
    story.append(Spacer(1, 4))

    # Azure CLI Commands Box
    cli_code = (
        "# 1. Create Azure Resource Group & ACR\n"
        "az group create --name rg-insight-prod --location eastus\n"
        "az acr create --resource-group rg-insight-prod --name insightacr --sku Basic --admin-enabled true\n\n"
        "# 2. Deploy Container App with Scale-to-Zero\n"
        "az containerapp create --name insight-backend --resource-group rg-insight-prod \\\n"
        "  --image insightacr.azurecr.io/insight-backend:latest --target-port 8000 --ingress external \\\n"
        "  --min-replicas 0 --max-replicas 3 --cpu 0.5 --memory 1.0Gi\n\n"
        "# 3. Configure Hard Cost Management Alert ($20 limit)\n"
        "az consumption budget create --budget-name InSightBudget --amount 20 --category Cost"
    )
    story.append(b.code_box(cli_code, label="AZURE SERVERLESS DEPLOYMENT & GOVERNANCE SCRIPT"))

    return story
