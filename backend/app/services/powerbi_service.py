import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "powerbi_config.json"

DEFAULT_SAMPLE_EMBED_URL = "https://app.powerbi.com/view?r=eyJrIjoiMDMwYTE3MWMtOWFlNy00NGNlLWJmZTAtZDJjNDc4NTgzOGQzIiwidCI6IjVmMmEwODJiLTdiMDQtNDNmOS1hOGUwLTViZTE0ZDVjYWE4MyIsImMiOjF9"


class PowerBIService:
    """
    Enterprise Microsoft Power BI Service & Azure Entra ID Embedded Service.
    
    Implements the official Microsoft "App Owns Data" / Service Principal pattern:
    1. Authenticates against Microsoft Entra ID (login.microsoftonline.com) via OAuth2 client_credentials.
    2. Queries the Power BI REST API (api.powerbi.com) for report metadata and embedUrl.
    3. Mints secure, short-lived Power BI Embed Tokens (EmbedToken) for client-side embedding.
    4. Triggers automated semantic model / dataset refreshes upon new telemetry ingestion.
    """

    def __init__(self):
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Azure Entra ID & Power BI Service Configuration Status
    # -------------------------------------------------------------------------

    @staticmethod
    def get_azure_config_status() -> Dict[str, Any]:
        """
        Evaluates whether Azure App Registration and Power BI Service credentials
        are configured in environment variables.
        """
        tenant_id = (settings.POWERBI_TENANT_ID or "").strip()
        client_id = (settings.POWERBI_CLIENT_ID or "").strip()
        client_secret = (settings.POWERBI_CLIENT_SECRET or "").strip()
        workspace_id = (settings.POWERBI_WORKSPACE_ID or "").strip()
        report_id = (settings.POWERBI_REPORT_ID or "").strip()
        dataset_id = (settings.POWERBI_DATASET_ID or "").strip()

        missing_keys: List[str] = []
        if not tenant_id:
            missing_keys.append("POWERBI_TENANT_ID")
        if not client_id:
            missing_keys.append("POWERBI_CLIENT_ID")
        if not client_secret:
            missing_keys.append("POWERBI_CLIENT_SECRET")
        if not workspace_id:
            missing_keys.append("POWERBI_WORKSPACE_ID")
        if not report_id:
            missing_keys.append("POWERBI_REPORT_ID")

        is_configured = len(missing_keys) == 0

        return {
            "is_configured": is_configured,
            "architecture": "Microsoft Entra ID Service Principal (App Owns Data)",
            "credentials_present": {
                "tenant_id": bool(tenant_id),
                "client_id": bool(client_id),
                "client_secret": bool(client_secret),
                "workspace_id": bool(workspace_id),
                "report_id": bool(report_id),
                "dataset_id": bool(dataset_id),
            },
            "workspace_id": workspace_id or None,
            "report_id": report_id or None,
            "dataset_id": dataset_id or None,
            "missing_keys": missing_keys,
        }

    # -------------------------------------------------------------------------
    # 2. Azure Entra ID Token Acquisition
    # -------------------------------------------------------------------------

    def acquire_azure_ad_token(self) -> str:
        """
        Acquires an Azure AD access token for the Power BI service using client credentials grant.
        """
        cfg = self.get_azure_config_status()
        if not cfg["is_configured"]:
            missing = ", ".join(cfg["missing_keys"])
            raise ValueError(f"Missing required Azure/Power BI configuration: {missing}")

        token_url = f"{settings.POWERBI_AUTHORITY_URL.rstrip('/')}/{settings.POWERBI_TENANT_ID}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.POWERBI_CLIENT_ID,
            "client_secret": settings.POWERBI_CLIENT_SECRET,
            "scope": settings.POWERBI_SCOPE,
        }

        try:
            response = requests.post(token_url, data=payload, timeout=12)
        except Exception as e:
            logger.error(f"Failed to connect to Azure Entra ID token endpoint: {e}")
            raise ConnectionError(f"Network error contacting Azure Entra ID: {str(e)}")

        if response.status_code != 200:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            err_desc = error_data.get("error_description", response.text)
            logger.error(f"Azure AD token acquisition failed ({response.status_code}): {err_desc}")
            raise PermissionError(f"Azure AD authentication rejected ({response.status_code}): {err_desc}")

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Azure AD response did not include access_token")

        return access_token

    # -------------------------------------------------------------------------
    # 3. Power BI REST API: Report Metadata & Embed Token Minting
    # -------------------------------------------------------------------------

    def get_report_details(
        self,
        workspace_id: Optional[str] = None,
        report_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches official report metadata (name, embedUrl, datasetId) from Power BI Service.
        """
        target_ws = workspace_id or settings.POWERBI_WORKSPACE_ID
        target_rep = report_id or settings.POWERBI_REPORT_ID
        if not target_ws or not target_rep:
            raise ValueError("workspace_id and report_id must be provided or configured in environment")

        aad_token = self.acquire_azure_ad_token()
        headers = {
            "Authorization": f"Bearer {aad_token}",
            "Content-Type": "application/json"
        }
        url = f"{settings.POWERBI_API_URL.rstrip('/')}/groups/{target_ws}/reports/{target_rep}"

        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                pass
            raise RuntimeError(
                f"Power BI API error fetching report ({response.status_code}): {error_detail}. "
                "Ensure the Azure App Registration has been granted access to this Power BI workspace."
            )

        return response.json()

    def generate_embed_token(
        self,
        workspace_id: Optional[str] = None,
        report_id: Optional[str] = None,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mints a short-lived Power BI Embed Token for secure in-app rendering.
        """
        target_ws = workspace_id or settings.POWERBI_WORKSPACE_ID
        target_rep = report_id or settings.POWERBI_REPORT_ID
        target_ds = dataset_id or settings.POWERBI_DATASET_ID

        # First retrieve report to get official embedUrl and datasetId if not set
        report_info = self.get_report_details(target_ws, target_rep)
        embed_url = report_info.get("embedUrl")
        report_name = report_info.get("name", "InSight Review Intelligence")
        actual_dataset_id = target_ds or report_info.get("datasetId")

        aad_token = self.acquire_azure_ad_token()
        headers = {
            "Authorization": f"Bearer {aad_token}",
            "Content-Type": "application/json"
        }

        token_url = f"{settings.POWERBI_API_URL.rstrip('/')}/groups/{target_ws}/reports/{target_rep}/GenerateToken"
        body = {
            "accessLevel": "View",
            "allowSaveAs": False
        }
        if actual_dataset_id:
            body["datasetId"] = actual_dataset_id

        response = requests.post(token_url, headers=headers, json=body, timeout=12)
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                pass
            raise RuntimeError(f"Power BI API GenerateToken failed ({response.status_code}): {error_detail}")

        token_result = response.json()

        return {
            "status": "success",
            "report_id": target_rep,
            "workspace_id": target_ws,
            "dataset_id": actual_dataset_id,
            "report_title": report_name,
            "embed_url": embed_url,
            "embed_token": token_result.get("token"),
            "token_id": token_result.get("tokenId"),
            "expiration": token_result.get("expiration"),
        }

    # -------------------------------------------------------------------------
    # 4. Trigger Semantic Model / Dataset Refresh
    # -------------------------------------------------------------------------

    def trigger_dataset_refresh(
        self,
        workspace_id: Optional[str] = None,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Instructs Microsoft Power BI Service to execute a real-time refresh on the
        semantic model / dataset so updated InSight telemetry is pulled in immediately.
        """
        target_ws = workspace_id or settings.POWERBI_WORKSPACE_ID
        target_ds = dataset_id or settings.POWERBI_DATASET_ID

        if not target_ws or not target_ds:
            raise ValueError("workspace_id and dataset_id are required to trigger dataset refresh.")

        aad_token = self.acquire_azure_ad_token()
        headers = {
            "Authorization": f"Bearer {aad_token}",
            "Content-Type": "application/json"
        }
        url = f"{settings.POWERBI_API_URL.rstrip('/')}/groups/{target_ws}/datasets/{target_ds}/refreshes"

        # POST with body {} triggers an asynchronous refresh in Power BI
        response = requests.post(url, headers=headers, json={"notifyOption": "NoNotification"}, timeout=12)
        if response.status_code not in (200, 202):
            error_detail = response.text
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                pass
            raise RuntimeError(f"Dataset refresh request failed ({response.status_code}): {error_detail}")

        return {
            "status": "triggered",
            "workspace_id": target_ws,
            "dataset_id": target_ds,
            "http_status": response.status_code,
            "message": "Power BI semantic model refresh initiated successfully."
        }

    # -------------------------------------------------------------------------
    # 5. Connection Health Diagnostic
    # -------------------------------------------------------------------------

    def test_connection(self) -> Dict[str, Any]:
        """
        Runs a step-by-step diagnostic on Azure Entra ID and Power BI Service access.
        """
        status_info = self.get_azure_config_status()
        if not status_info["is_configured"]:
            return {
                "connected": False,
                "step": "configuration",
                "message": "Environment variables are not configured.",
                "missing_keys": status_info["missing_keys"],
            }

        # Step 1: Azure AD Token
        try:
            aad_token = self.acquire_azure_ad_token()
        except Exception as e:
            return {
                "connected": False,
                "step": "azure_ad_token",
                "message": f"Azure Entra ID authentication failed: {str(e)}",
            }

        # Step 2: Power BI Report Access
        try:
            report_info = self.get_report_details()
        except Exception as e:
            return {
                "connected": False,
                "step": "powerbi_report_access",
                "message": f"Power BI Service report access failed: {str(e)}",
            }

        # Step 3: Embed Token Generation
        try:
            embed_res = self.generate_embed_token()
        except Exception as e:
            return {
                "connected": False,
                "step": "powerbi_embed_token",
                "message": f"Power BI Embed Token generation failed: {str(e)}",
            }

        return {
            "connected": True,
            "report_name": report_info.get("name"),
            "report_id": embed_res.get("report_id"),
            "workspace_id": embed_res.get("workspace_id"),
            "token_expiration": embed_res.get("expiration"),
            "message": "Successfully verified Microsoft Entra ID authentication & Power BI Service embed token.",
        }

    # -------------------------------------------------------------------------
    # 6. Legacy / Local URL Config Persistence (Fallback)
    # -------------------------------------------------------------------------

    def get_config(self) -> Dict[str, Any]:
        """Returns local config fallback (if user wants to test a public or direct URL)."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read Power BI config file: {e}")

        return {
            "embed_url": "",
            "report_title": "InSight Executive Review Intelligence",
            "is_configured": False,
            "demo_url": DEFAULT_SAMPLE_EMBED_URL,
            "last_updated": None,
        }

    def save_config(self, embed_url: str, report_title: Optional[str] = None) -> Dict[str, Any]:
        """Saves local embed URL configuration to disk."""
        self._ensure_config_dir()
        current = self.get_config()
        clean_url = (embed_url or "").strip()

        updated = {
            "embed_url": clean_url,
            "report_title": (report_title or current.get("report_title", "InSight Executive Review Intelligence")).strip(),
            "is_configured": bool(clean_url),
            "demo_url": DEFAULT_SAMPLE_EMBED_URL,
            "last_updated": str(Path(__file__).stat().st_mtime),
        }

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write Power BI config file: {e}")

        return updated

    # -------------------------------------------------------------------------
    # 7. Templates & Schema Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def generate_pbids_content(base_api_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
        """Generates Microsoft Power BI Data Source (.pbids) JSON structure."""
        normalized_base = base_api_url.rstrip("/")
        feed_url = f"{normalized_base}/api/powerbi/data/reviews.csv"
        return {
            "version": "0.1",
            "connections": [
                {
                    "details": {
                        "url": feed_url
                    },
                    "connectionType": "Web"
                }
            ]
        }

    @staticmethod
    def get_powerquery_m_snippet(base_api_url: str = "http://127.0.0.1:8000") -> str:
        """Returns pre-formulated Power Query (M) script for copy-paste in Power BI Desktop."""
        feed_url = f"{base_api_url.rstrip('/')}/api/powerbi/data/reviews.csv"
        return f"""let
    // 1. Connect to InSight live telemetry CSV endpoint
    Source = Csv.Document(Web.Contents("{feed_url}"), [Delimiter=",", Columns=20, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    
    // 2. Promote first row to column headers
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    
    // 3. Enforce strong Power BI data types for optimal VertiPaq compression
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{
        {{"Review_ID", type text}},
        {{"Domain", type text}},
        {{"Product_Name", type text}},
        {{"SKU_or_Module", type text}},
        {{"Batch_or_Version", type text}},
        {{"Submission_Date", type datetime}},
        {{"Channel", type text}},
        {{"Rating", Int64.Type}},
        {{"Calibrated_Sentiment", type text}},
        {{"Sentiment_Confidence", type number}},
        {{"Theme_Title", type text}},
        {{"Cluster_ID", Int64.Type}},
        {{"Sentence_Count", Int64.Type}},
        {{"Complaint_Clauses", Int64.Type}},
        {{"Praise_Clauses", Int64.Type}},
        {{"Recommendation_Clauses", Int64.Type}},
        {{"Is_Actionable", type logical}},
        {{"Has_Silent_Defect", type logical}},
        {{"Is_PII_Scrubbed", type logical}},
        {{"Sanitized_Verbatim", type text}}
    }})
in
    #"Changed Type"
"""

    @staticmethod
    def get_dax_measures() -> list:
        """Returns catalog of pre-built DAX measures for executive reporting."""
        return [
            {
                "id": "nss",
                "name": "Net Sentiment Score (NSS)",
                "category": "Sentiment & Trust",
                "description": "Calculates Net Sentiment Score: (% Positive Reviews - % Negative Reviews), scaled from -100 to +100.",
                "dax": """Net Sentiment Score (NSS) = 
VAR TotalReviews = COUNTROWS(Fact_ReviewTelemetry)
VAR PosCount = CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Calibrated_Sentiment] = "POSITIVE")
VAR NegCount = CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Calibrated_Sentiment] = "NEGATIVE")
RETURN
IF(TotalReviews = 0, 0, DIVIDE(PosCount - NegCount, TotalReviews, 0) * 100)"""
            },
            {
                "id": "defect_rate",
                "name": "Defect Surge Rate (%)",
                "category": "Quality & Operations",
                "description": "Percentage of customer verbatims that contain verified defect or complaint clauses.",
                "dax": """Defect Surge Rate (%) = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Complaint_Clauses] > 0),
    COUNTROWS(Fact_ReviewTelemetry),
    0
) * 100"""
            },
            {
                "id": "silent_defects",
                "name": "Trojan Horse Defect Citations",
                "category": "Zero-Day Detection",
                "description": "Number of high-star ratings (4★ to 5★) that conceal critical product defects or packaging flaws.",
                "dax": """Trojan Horse Defect Citations = 
CALCULATE(
    COUNTROWS(Fact_ReviewTelemetry),
    Fact_ReviewTelemetry[Has_Silent_Defect] = TRUE()
)"""
            },
            {
                "id": "actionable_telemetry",
                "name": "Actionable Telemetry Rate (%)",
                "category": "Signal Intelligence",
                "description": "Percentage of reviews delivering tangible product signal (Complaints, Recommendations, or Praise).",
                "dax": """Actionable Telemetry Rate (%) = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Is_Actionable] = TRUE()),
    COUNTROWS(Fact_ReviewTelemetry),
    0
) * 100"""
            },
            {
                "id": "pii_compliance",
                "name": "GDPR / PII Redaction Compliance (%)",
                "category": "Governance & Security",
                "description": "Audit proof demonstrating that 100% of customer reviews underwent zero-trust PII redaction.",
                "dax": """PII Redaction Rate (%) = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_ReviewTelemetry), Fact_ReviewTelemetry[Is_PII_Scrubbed] = TRUE()),
    COUNTROWS(Fact_ReviewTelemetry),
    0
) * 100"""
            },
            {
                "id": "severe_incidents",
                "name": "Severe Incidents (P0/P1 Volume)",
                "category": "Engineering Triage",
                "description": "Total volume of customer complaints falling into 1★-2★ negative severity band.",
                "dax": """Severe P0-P1 Incidents = 
CALCULATE(
    COUNTROWS(Fact_ReviewTelemetry),
    Fact_ReviewTelemetry[Complaint_Clauses] > 0,
    Fact_ReviewTelemetry[Rating] <= 2
)"""
            }
        ]


powerbi_service = PowerBIService()
