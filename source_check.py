"""
source_check.py
===============
Preflight source health diagnostic utility for LegalLens.

Audits each configured legal data source for:
1. robots.txt accessibility and policy decision (ALLOW, DISALLOW, UNKNOWN)
2. Network / DNS reachability of the base domain
3. Configured index paths availability
4. API keys and authentication configuration
5. Distinguishes manual sources (eCourts) from automated sources

Statuses reported:
- READY: Source base and index paths are reachable and allowed by robots.
- PARTIAL: Base domain is reachable, but some index paths or optional endpoints returned errors.
- MANUAL: Source is manual-only by design (e.g. eCourts CAPTCHA/OTP barrier).
- BLOCKED: Source explicitly disallows bot access via robots.txt or WAF (403).
- UNKNOWN: Network timeout, DNS resolution failure, or unresolvable connection.

Usage:
    python source_check.py [--sources nalsa,meity] [--json]
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import httpx
from rich.console import Console
from rich.table import Table

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.core.config import get_config
from pipeline.core.http_client import LegalLensClient, RobotsCache, RobotsDecision, redact_secrets_from_url

console = Console()


async def check_source_health(source_id: str, cfg) -> Dict[str, Any]:
    """Audit a single source and return structured diagnostics."""
    if source_id == "ecourts":
        return {
            "source_id": "ecourts",
            "name": "eCourts Services",
            "status": "MANUAL",
            "robots": "N/A",
            "http_status": "N/A",
            "reason": "Automated requests disabled. CAPTCHA/OTP barrier. See MANUAL_INGESTION.md",
        }

    src_cfg = getattr(cfg.sources, source_id, None)
    if src_cfg is None:
        return {
            "source_id": source_id,
            "name": source_id,
            "status": "UNKNOWN",
            "robots": "UNKNOWN",
            "http_status": "N/A",
            "reason": "Source not configured in config.yaml",
        }

    if not getattr(src_cfg, "enabled", True):
        return {
            "source_id": source_id,
            "name": getattr(src_cfg, "name", source_id),
            "status": "DISABLED",
            "robots": "N/A",
            "http_status": "N/A",
            "reason": "Disabled in config.yaml",
        }

    base_url = getattr(src_cfg, "base_url", "")
    index_paths = getattr(src_cfg, "index_paths", [])

    # Special handling for data_gov
    if source_id == "data_gov":
        api_key = cfg.data_gov_api_key
        api_base = cfg.data_gov_api_base
        if not api_key:
            return {
                "source_id": source_id,
                "name": "data.gov.in",
                "status": "BLOCKED",
                "robots": "N/A",
                "http_status": "N/A",
                "reason": "DATA_GOV_API_KEY not set in .env. Register at data.gov.in",
            }
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as test_client:
                test_url = f"{api_base}/catalog/all?api-key={api_key}&format=json&limit=1"
                resp = await test_client.get(test_url)
                if resp.status_code == 200:
                    return {
                        "source_id": source_id,
                        "name": "data.gov.in",
                        "status": "READY",
                        "robots": "ALLOW",
                        "http_status": 200,
                        "reason": "Official API operational with valid API key",
                    }
                else:
                    return {
                        "source_id": source_id,
                        "name": "data.gov.in",
                        "status": "PARTIAL",
                        "robots": "ALLOW",
                        "http_status": resp.status_code,
                        "reason": f"API returned HTTP {resp.status_code}",
                    }
        except Exception as exc:
            return {
                "source_id": source_id,
                "name": "data.gov.in",
                "status": "UNKNOWN",
                "robots": "UNKNOWN",
                "http_status": "ERR",
                "reason": redact_secrets_from_url(str(exc)),
            }

    # Special handling for india_code_api
    if source_id == "india_code_api":
        api_base = cfg.india_code_api_base
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as test_client:
                resp = await test_client.get(f"{api_base}/v1/search?q=contract")
                if resp.status_code == 200:
                    return {
                        "source_id": source_id,
                        "name": "India Code API (ecourtsindia)",
                        "status": "READY",
                        "robots": "ALLOW",
                        "http_status": 200,
                        "reason": "Community API endpoint responsive",
                    }
                else:
                    return {
                        "source_id": source_id,
                        "name": "India Code API",
                        "status": "PARTIAL",
                        "robots": "UNKNOWN",
                        "http_status": resp.status_code,
                        "reason": f"API returned HTTP {resp.status_code}",
                    }
        except Exception as exc:
            return {
                "source_id": source_id,
                "name": "India Code API",
                "status": "UNKNOWN",
                "robots": "UNKNOWN",
                "http_status": "ERR",
                "reason": str(exc),
            }

    # Web scraping sources (india_code, nalsa, supreme_court, legislative_dept, meity)
    robots_cache = RobotsCache(
        audit_log_path=str(Path(cfg.storage.logs_dir) / "robots_audit.jsonl"),
        unknown_policy=cfg.collection.robots_unknown_policy,
    )

    robots_decision = await robots_cache.check_url(base_url, user_agent=cfg.collection.user_agent)
    robots_str = robots_decision.value

    # Check base domain reachability
    base_http_status = None
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": cfg.collection.user_agent},
            verify=False,
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            base_resp = await client.get(base_url)
            base_http_status = base_resp.status_code
    except Exception as exc:
        return {
            "source_id": source_id,
            "name": getattr(src_cfg, "name", source_id),
            "status": "UNKNOWN",
            "robots": robots_str,
            "http_status": "ERR",
            "reason": f"Connection error: {exc}",
        }

    if base_http_status == 403:
        return {
            "source_id": source_id,
            "name": getattr(src_cfg, "name", source_id),
            "status": "BLOCKED",
            "robots": robots_str,
            "http_status": 403,
            "reason": "Base URL returned HTTP 403 Forbidden (WAF/bot block)",
        }

    if robots_decision == RobotsDecision.DISALLOW:
        return {
            "source_id": source_id,
            "name": getattr(src_cfg, "name", source_id),
            "status": "BLOCKED",
            "robots": robots_str,
            "http_status": base_http_status,
            "reason": f"robots.txt disallowed for user-agent",
        }

    # Check configured index paths
    index_results = []
    if index_paths:
        async with httpx.AsyncClient(
            headers={"User-Agent": cfg.collection.user_agent},
            verify=False,
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            for ipath in index_paths:
                full_path_url = base_url.rstrip("/") + "/" + ipath.lstrip("/")
                p_decision = await robots_cache.check_url(full_path_url, user_agent=cfg.collection.user_agent)
                if p_decision == RobotsDecision.DISALLOW:
                    index_results.append((ipath, "ROBOTS_DISALLOWED", None))
                    continue
                try:
                    resp = await client.get(full_path_url)
                    index_results.append((ipath, "OK" if resp.status_code == 200 else "FAIL", resp.status_code))
                except Exception as exc:
                    index_results.append((ipath, "ERR", str(exc)))

    # Compute overall status
    if not index_results:
        status = "READY" if base_http_status in (200, 301, 302) else "PARTIAL"
        reason = f"Base URL returned HTTP {base_http_status}"
    else:
        ok_count = sum(1 for _, st, code in index_results if st == "OK")
        blocked_count = sum(1 for _, st, code in index_results if code == 403 or st == "ROBOTS_DISALLOWED")
        if ok_count == len(index_results):
            status = "READY"
            reason = f"All {ok_count} index path(s) accessible"
        elif ok_count > 0:
            status = "PARTIAL"
            reason = f"{ok_count}/{len(index_results)} index path(s) accessible"
        elif blocked_count > 0:
            status = "BLOCKED"
            reason = "Index paths blocked by WAF (403) or robots.txt"
        else:
            status = "PARTIAL"
            reason = f"Index paths returned non-200: {[code for _, _, code in index_results]}"

    return {
        "source_id": source_id,
        "name": getattr(src_cfg, "name", source_id),
        "status": status,
        "robots": robots_str,
        "http_status": base_http_status,
        "reason": reason,
        "index_paths_checked": len(index_results),
    }


async def run_diagnostics(source_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    cfg = get_config()
    all_sources = [
        "india_code",
        "india_code_api",
        "data_gov",
        "ecourts",
        "supreme_court",
        "nalsa",
        "legislative_dept",
        "meity",
    ]
    target_sources = source_ids if source_ids else all_sources
    tasks = [check_source_health(s, cfg) for s in target_sources]
    return await asyncio.gather(*tasks)


def display_results(results: List[Dict[str, Any]]) -> None:
    table = Table(title="LegalLens Source Health & Preflight Diagnostics", header_style="bold magenta")
    table.add_column("Source ID", style="bold")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Robots")
    table.add_column("Base HTTP")
    table.add_column("Diagnostic Reason")

    status_styles = {
        "READY": "[bold green]READY[/bold green]",
        "PARTIAL": "[bold yellow]PARTIAL[/bold yellow]",
        "MANUAL": "[bold cyan]MANUAL[/bold cyan]",
        "BLOCKED": "[bold red]BLOCKED[/bold red]",
        "UNKNOWN": "[bold magenta]UNKNOWN[/bold magenta]",
        "DISABLED": "[dim]DISABLED[/dim]",
    }

    for r in results:
        styled_status = status_styles.get(r["status"], r["status"])
        table.add_row(
            r["source_id"],
            r["name"][:30],
            styled_status,
            r.get("robots", "-"),
            str(r.get("http_status", "-")),
            r.get("reason", "")[:60],
        )

    console.print(table)


@click.command()
@click.option("--sources", default=None, help="Comma-separated source IDs to check")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output results in JSON format")
def cli(sources: Optional[str], output_json: bool) -> None:
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    results = asyncio.run(run_diagnostics(source_list))
    if output_json:
        click.echo(json.dumps(results, indent=2))
    else:
        display_results(results)


if __name__ == "__main__":
    cli()
