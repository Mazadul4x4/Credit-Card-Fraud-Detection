"""Microsoft Teams notifications (Adaptive Card through a Teams "Workflows" webhook,
also accepted by legacy Incoming Webhooks)."""

import logging

import requests

logger = logging.getLogger(__name__)

COLORS = {"HIGH": "Attention", "MEDIUM": "Warning", "LOW": "Good"}


def report_link(report_path: str, base_url: str) -> str:
    """Clickable link if a Data Docs base URL is configured (nginx, Defense 2),
    otherwise just the report path inside gx_project/gx/uncommitted/data_docs/local_site/."""
    if not report_path:
        return ""
    if base_url:
        return f"{base_url.rstrip('/')}/{report_path}"
    return report_path


def build_data_quality_card(file_name: str, summary: dict, report: str) -> dict:
    criticality = summary["criticality"]
    errors = ", ".join(f"{k}: {v}" for k, v in summary["error_counts"].items() if v) or "none"
    facts = [
        {"title": "File", "value": file_name},
        {"title": "Criticality", "value": criticality},
        {"title": "Invalid rows", "value": f"{summary['invalid_rows']} / {summary['total_rows']} "
                                          f"({summary['invalid_ratio']:.0%})"},
        {"title": "Errors (rows)", "value": errors},
        {"title": "Missing columns", "value": ", ".join(summary["missing_columns"]) or "none"},
        {"title": "Report", "value": report or "n/a"},
    ]
    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "color": COLORS.get(criticality, "Default"),
            "text": f"Data quality alert | {criticality}",
        },
        {"type": "FactSet", "facts": facts},
    ]
    actions = []
    if report.startswith("http"):
        actions.append({"type": "Action.OpenUrl", "title": "Open Data Docs report", "url": report})
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                    "actions": actions,
                },
            }
        ],
    }


def send_teams(webhook_url: str, card: dict) -> bool:
    if not webhook_url:
        logger.warning("No Teams webhook configured, alert not sent:\n%s", card)
        return False
    response = requests.post(webhook_url, json=card, timeout=15)
    response.raise_for_status()
    return True
