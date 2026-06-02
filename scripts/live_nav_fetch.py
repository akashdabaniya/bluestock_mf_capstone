#!/usr/bin/env python3
"""
live_nav_fetch.py — Live NAV Fetcher for Bluestock Mutual Fund Capstone
========================================================================

Fetches the most-recent (live) NAV for the 6 core tracked schemes,
saves individual CSVs and a consolidated summary.

Can be run as a standalone script **or** imported as a module::

    # Standalone
    python scripts/live_nav_fetch.py

    # As a module
    from scripts.live_nav_fetch import fetch_live_navs
    summary_df = fetch_live_navs()

Author : Akash Dabaniya (@akashdabaniya)
Date   : 2026-06-02
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

DIR_RAW: Path = PROJECT_ROOT / "data" / "raw"
DIR_PROCESSED: Path = PROJECT_ROOT / "data" / "processed"

MFAPI_BASE_URL: str = "https://api.mfapi.in/mf"

# The 6 key schemes specified in the task
LIVE_SCHEMES: dict[str, int] = {
    "HDFC Top 100 Direct":   125497,
    "SBI Bluechip Direct":   119551,
    "ICICI Bluechip Direct": 120503,
    "Nippon Large Cap Direct": 118632,
    "Axis Bluechip Direct":  119092,
    "Kotak Bluechip Direct": 120841,
}

REQUEST_TIMEOUT_SEC: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_SEC: float = 2.0
RATE_LIMIT_SEC: float = 1.0

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _api_get(url: str) -> Any:
    """GET with retries and exponential back-off.

    Parameters
    ----------
    url : str
        Target URL.

    Returns
    -------
    Any
        Parsed JSON.

    Raises
    ------
    requests.HTTPError
        After exhausting all retry attempts.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            wait = RETRY_BACKOFF_SEC * attempt
            logger.warning(
                "Attempt %d/%d for %s failed: %s — retrying in %.1fs",
                attempt, MAX_RETRIES, url, exc, wait,
            )
            if attempt == MAX_RETRIES:
                raise
            time.sleep(wait)


def _rate_limit() -> None:
    """Pause between API calls to stay within rate limits."""
    time.sleep(RATE_LIMIT_SEC)

# ──────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────


def fetch_single_live_nav(
    scheme_code: int,
    scheme_label: str,
) -> dict[str, Any] | None:
    """Fetch the latest NAV for a single scheme.

    Parameters
    ----------
    scheme_code : int
        AMFI scheme code.
    scheme_label : str
        Human-readable scheme name.

    Returns
    -------
    dict or None
        Keys: ``scheme_code``, ``scheme_name``, ``fund_house``,
        ``nav_date``, ``nav_value``, ``fetched_at``.
        Returns ``None`` on failure.
    """
    url = f"{MFAPI_BASE_URL}/{scheme_code}"
    try:
        payload = _api_get(url)
    except Exception:
        logger.exception("Could not fetch live NAV for %s (%d)", scheme_label, scheme_code)
        return None

    meta: dict = payload.get("meta", {})
    nav_data: list[dict] = payload.get("data", [])

    if not nav_data:
        logger.warning("No NAV data in response for %s (%d)", scheme_label, scheme_code)
        return None

    latest = nav_data[0]  # the API returns most-recent first
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    record = {
        "scheme_code": scheme_code,
        "scheme_name": meta.get("scheme_name", scheme_label),
        "fund_house": meta.get("fund_house", "N/A"),
        "nav_date": latest.get("date", "N/A"),
        "nav_value": latest.get("nav", "N/A"),
        "fetched_at": fetched_at,
    }

    # Save individual file
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    individual_path: Path = DIR_RAW / f"live_nav_{scheme_code}.csv"
    pd.DataFrame([record]).to_csv(individual_path, index=False)
    logger.info(
        "Saved live_nav_%d.csv  →  %s",
        scheme_code, individual_path.relative_to(PROJECT_ROOT),
    )

    return record


def fetch_live_navs() -> pd.DataFrame:
    """Fetch live NAVs for all 6 key schemes and build a summary table.

    Returns
    -------
    pd.DataFrame
        Consolidated summary with one row per scheme.
    """
    records: list[dict[str, Any]] = []

    for label, code in LIVE_SCHEMES.items():
        result = fetch_single_live_nav(code, label)
        if result is not None:
            records.append(result)
        _rate_limit()

    if not records:
        logger.error("No live NAVs could be fetched.")
        return pd.DataFrame()

    summary = pd.DataFrame(records)

    # Persist consolidated summary
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    summary_path: Path = DIR_PROCESSED / "live_nav_summary.csv"
    summary.to_csv(summary_path, index=False)
    logger.info(
        "Saved live_nav_summary.csv  →  %s",
        summary_path.relative_to(PROJECT_ROOT),
    )

    # Pretty-print
    logger.info("─── Live NAV Summary ───")
    header = f"{'Scheme Name':<45} {'NAV':>10} {'Date':>12}"
    logger.info(header)
    logger.info("─" * len(header))
    for _, row in summary.iterrows():
        logger.info(
            "%-45s %10s %12s",
            row["scheme_name"][:45],
            row["nav_value"],
            row["nav_date"],
        )

    return summary


# ──────────────────────────────────────────────
# CLI entry-point
# ──────────────────────────────────────────────


def main() -> None:
    """Run the live NAV fetch workflow."""
    logger.info("🔄 Starting Live NAV Fetch — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary = fetch_live_navs()
    if not summary.empty:
        logger.info("✅ Live NAV fetch complete — %d schemes retrieved.", len(summary))
    else:
        logger.error("❌ Live NAV fetch finished with no data.")


if __name__ == "__main__":
    main()
