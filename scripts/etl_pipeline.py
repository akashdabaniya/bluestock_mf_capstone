#!/usr/bin/env python3
"""
etl_pipeline.py — Day 1 ETL Pipeline for Bluestock Mutual Fund Capstone
========================================================================

Deliverable D1 (Weight: 15 %)

This script performs end-to-end data ingestion:
    1. Creates the full project folder structure.
    2. Fetches the complete AMFI fund-master list.
    3. Downloads NAV history for 10 key mutual-fund schemes.
    4. Merges individual NAVs into a combined, calendar-indexed DataFrame.
    5. Validates AMFI scheme codes.
    6. Writes a data-quality summary report.

Usage:
    python scripts/etl_pipeline.py

Author : Your Name
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

# Project root is *two* levels up from this script file:
#   bluestock_mf_capstone/scripts/etl_pipeline.py  →  bluestock_mf_capstone/
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Sub-directory layout
DIR_RAW: Path = PROJECT_ROOT / "data" / "raw"
DIR_PROCESSED: Path = PROJECT_ROOT / "data" / "processed"
DIR_DB: Path = PROJECT_ROOT / "data" / "db"
DIR_NOTEBOOKS: Path = PROJECT_ROOT / "notebooks"
DIR_SCRIPTS: Path = PROJECT_ROOT / "scripts"
DIR_SQL: Path = PROJECT_ROOT / "sql"
DIR_DASHBOARD: Path = PROJECT_ROOT / "dashboard"
DIR_REPORTS: Path = PROJECT_ROOT / "reports"

ALL_DIRS: list[Path] = [
    DIR_RAW, DIR_PROCESSED, DIR_DB,
    DIR_NOTEBOOKS, DIR_SCRIPTS, DIR_SQL,
    DIR_DASHBOARD, DIR_REPORTS,
]

# MFAPI endpoints
MFAPI_BASE_URL: str = "https://api.mfapi.in/mf"

# Key schemes to track  (label → AMFI scheme_code)
KEY_SCHEMES: dict[str, int] = {
    "HDFC Top 100 Direct":              125497,
    "SBI Bluechip Direct":              119551,
    "ICICI Bluechip Direct":            120503,
    "Nippon Large Cap Direct":          118632,
    "Axis Bluechip Direct":             119092,
    "Kotak Bluechip Direct":            120841,
    "HDFC Mid-Cap Opportunities Direct": 118989,
    "Parag Parikh Flexi Cap Direct":    122639,
    "Mirae Asset Large Cap Direct":     118834,
    "SBI Small Cap Direct":             125497,
}

# Deduplicated codes (125497 appears twice)
UNIQUE_SCHEME_CODES: list[int] = sorted(set(KEY_SCHEMES.values()))

# Networking
REQUEST_TIMEOUT_SEC: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_SEC: float = 2.0
RATE_LIMIT_SEC: float = 1.0   # minimum gap between consecutive API calls

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
# Helper utilities
# ──────────────────────────────────────────────


def create_folder_structure() -> None:
    """Create every project sub-directory (idempotent)."""
    for directory in ALL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
        logger.info("Directory ready: %s", directory.relative_to(PROJECT_ROOT))


def _api_get(url: str) -> Any:
    """Perform a GET request with retries and exponential back-off.

    Parameters
    ----------
    url : str
        Fully-qualified URL to fetch.

    Returns
    -------
    Any
        Parsed JSON payload.

    Raises
    ------
    requests.HTTPError
        If the request fails after *MAX_RETRIES* attempts.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            wait = RETRY_BACKOFF_SEC * attempt
            logger.warning(
                "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                attempt, MAX_RETRIES, url, exc, wait,
            )
            if attempt == MAX_RETRIES:
                logger.error("All %d attempts exhausted for %s", MAX_RETRIES, url)
                raise
            time.sleep(wait)


def _rate_limit() -> None:
    """Sleep to respect API rate-limit."""
    time.sleep(RATE_LIMIT_SEC)

# ──────────────────────────────────────────────
# Core ETL steps
# ──────────────────────────────────────────────


def fetch_fund_master() -> pd.DataFrame:
    """Download the full AMFI scheme master list and persist it as CSV.

    Returns
    -------
    pd.DataFrame
        The fund-master DataFrame.
    """
    logger.info("Fetching full AMFI fund-master list from %s …", MFAPI_BASE_URL)
    data = _api_get(MFAPI_BASE_URL)

    df = pd.DataFrame(data)
    output_path: Path = DIR_RAW / "fund_master.csv"
    df.to_csv(output_path, index=False)
    logger.info("Saved fund_master.csv  →  %s", output_path.relative_to(PROJECT_ROOT))

    # Exploration summary
    logger.info("fund_master shape : %s", df.shape)
    logger.info("fund_master dtypes:\n%s", df.dtypes.to_string())
    logger.info("fund_master head:\n%s", df.head().to_string())

    if "scheme_type" in df.columns:
        logger.info(
            "Unique fund houses        : %d",
            df.get("fund_house", pd.Series(dtype=str)).nunique(),
        )
        logger.info(
            "Unique scheme categories  : %d",
            df.get("scheme_category", pd.Series(dtype=str)).nunique(),
        )
        logger.info(
            "Unique scheme types       : %d",
            df.get("scheme_type", pd.Series(dtype=str)).nunique(),
        )
    else:
        # The /mf endpoint returns a flat list with scheme_code + scheme_name
        logger.info("Fund master columns: %s", list(df.columns))

    return df


def fetch_nav_history(scheme_code: int) -> pd.DataFrame:
    """Fetch historical NAV for a single scheme and save to CSV.

    Parameters
    ----------
    scheme_code : int
        AMFI scheme code.

    Returns
    -------
    pd.DataFrame
        Columns: ``date``, ``nav``.
    """
    url = f"{MFAPI_BASE_URL}/{scheme_code}"
    logger.info("Fetching NAV history for scheme %d …", scheme_code)
    payload = _api_get(url)

    meta: dict = payload.get("meta", {})
    nav_data: list[dict] = payload.get("data", [])

    if not nav_data:
        logger.warning("No NAV data returned for scheme %d", scheme_code)
        return pd.DataFrame(columns=["date", "nav"])

    df = pd.DataFrame(nav_data)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["date", "nav"])
    df = df.sort_values("date").reset_index(drop=True)

    # Persist individual raw file
    raw_path: Path = DIR_RAW / f"nav_{scheme_code}.csv"
    df.to_csv(raw_path, index=False)
    logger.info(
        "Saved nav_%d.csv  (%d rows)  →  %s",
        scheme_code, len(df), raw_path.relative_to(PROJECT_ROOT),
    )

    # Diagnostic prints
    logger.info("nav_%d  shape : %s", scheme_code, df.shape)
    logger.info("nav_%d  dtypes:\n%s", scheme_code, df.dtypes.to_string())
    logger.info("nav_%d  head:\n%s", scheme_code, df.head().to_string())

    # Attach meta for later use
    df.attrs["meta"] = meta
    return df


def build_combined_nav(
    nav_frames: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    """Merge individual NAV DataFrames into a single wide-format DataFrame.

    Columns are named ``nav_{scheme_code}``.  The index is a daily
    calendar date range; weekends / holidays are forward-filled.

    Parameters
    ----------
    nav_frames : dict[int, pd.DataFrame]
        Mapping of scheme_code → raw NAV DataFrame.

    Returns
    -------
    pd.DataFrame
        Combined, calendar-indexed NAV history.
    """
    if not nav_frames:
        logger.warning("No NAV frames to combine.")
        return pd.DataFrame()

    merged = pd.DataFrame()
    global_min_date = None
    global_max_date = None

    for code, df in nav_frames.items():
        if df.empty:
            continue
        series = df.set_index("date")["nav"].rename(f"nav_{code}")
        if merged.empty:
            merged = series.to_frame()
        else:
            merged = merged.join(series, how="outer")

        min_d, max_d = df["date"].min(), df["date"].max()
        global_min_date = min_d if global_min_date is None else min(global_min_date, min_d)
        global_max_date = max_d if global_max_date is None else max(global_max_date, max_d)

    if merged.empty:
        return merged

    # Reindex to full calendar range and forward-fill weekends/holidays
    full_range = pd.date_range(start=global_min_date, end=global_max_date, freq="D")
    merged = merged.reindex(full_range)
    merged = merged.ffill()  # always ffill after reindex
    merged.index.name = "date"

    # Persist
    output_path: Path = DIR_PROCESSED / "combined_nav_history.csv"
    merged.to_csv(output_path)
    logger.info(
        "Saved combined_nav_history.csv  (%s)  →  %s",
        merged.shape, output_path.relative_to(PROJECT_ROOT),
    )

    logger.info("combined_nav  shape : %s", merged.shape)
    logger.info("combined_nav  dtypes:\n%s", merged.dtypes.to_string())
    logger.info("combined_nav  head:\n%s", merged.head().to_string())

    return merged


def validate_amfi_codes(fund_master: pd.DataFrame) -> list[int]:
    """Check that every tracked scheme code exists in the fund master.

    Parameters
    ----------
    fund_master : pd.DataFrame
        The full AMFI scheme list.

    Returns
    -------
    list[int]
        List of scheme codes that were *not* found.
    """
    logger.info("Validating AMFI scheme codes …")

    # The /mf endpoint may use 'schemeCode' or 'scheme_code' — handle both
    code_col: str | None = None
    for candidate in ("schemeCode", "scheme_code"):
        if candidate in fund_master.columns:
            code_col = candidate
            break

    if code_col is None:
        logger.error(
            "Cannot validate: no scheme-code column found in fund_master (cols=%s)",
            list(fund_master.columns),
        )
        return list(UNIQUE_SCHEME_CODES)

    master_codes = set(fund_master[code_col].astype(int).unique())
    missing: list[int] = []
    for code in UNIQUE_SCHEME_CODES:
        if code in master_codes:
            logger.info("  ✓  Scheme %d found in fund master", code)
        else:
            logger.warning("  ✗  Scheme %d NOT found in fund master!", code)
            missing.append(code)

    return missing


def write_data_quality_report(
    fund_master: pd.DataFrame,
    nav_frames: dict[int, pd.DataFrame],
    combined: pd.DataFrame,
    missing_codes: list[int],
) -> None:
    """Write a plain-text data-quality summary to ``reports/``.

    Parameters
    ----------
    fund_master : pd.DataFrame
    nav_frames : dict[int, pd.DataFrame]
    combined : pd.DataFrame
    missing_codes : list[int]
    """
    report_path: Path = DIR_REPORTS / "data_quality_summary.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "=" * 72,
        "DATA QUALITY SUMMARY — Bluestock MF Capstone (Day 1)",
        f"Generated: {timestamp}",
        "=" * 72,
        "",
        "1. FUND MASTER",
        f"   Rows          : {len(fund_master)}",
        f"   Columns       : {list(fund_master.columns)}",
        f"   Null counts   :",
    ]
    for col in fund_master.columns:
        null_count = int(fund_master[col].isna().sum())
        lines.append(f"     {col:30s} : {null_count}")

    lines.append("")
    lines.append("2. INDIVIDUAL NAV FILES")
    for code, df in sorted(nav_frames.items()):
        null_nav = int(df["nav"].isna().sum()) if "nav" in df.columns else "N/A"
        date_range = "N/A"
        if not df.empty and "date" in df.columns:
            date_range = f"{df['date'].min().date()} → {df['date'].max().date()}"
        lines.append(
            f"   nav_{code}.csv : {len(df):>6} rows | "
            f"null NAVs: {null_nav} | range: {date_range}"
        )

    lines.append("")
    lines.append("3. COMBINED NAV HISTORY")
    lines.append(f"   Shape         : {combined.shape}")
    if not combined.empty:
        lines.append(f"   Date range    : {combined.index.min().date()} → {combined.index.max().date()}")
        lines.append(f"   Total nulls   : {int(combined.isna().sum().sum())}")
        lines.append("   Nulls per col :")
        for col in combined.columns:
            lines.append(f"     {col:30s} : {int(combined[col].isna().sum())}")

    lines.append("")
    lines.append("4. AMFI CODE VALIDATION")
    if missing_codes:
        lines.append(f"   Missing codes : {missing_codes}")
    else:
        lines.append("   All tracked scheme codes validated successfully ✓")

    lines.append("")
    lines.append("=" * 72)
    lines.append("END OF REPORT")
    lines.append("=" * 72)

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Data quality report  →  %s", report_path.relative_to(PROJECT_ROOT))

# ──────────────────────────────────────────────
# Fund master exploration helpers
# ──────────────────────────────────────────────


def explore_fund_master(fund_master: pd.DataFrame) -> None:
    """Print summary statistics about the fund master catalogue.

    Parameters
    ----------
    fund_master : pd.DataFrame
    """
    logger.info("─── Fund Master Exploration ───")

    # Determine the column names dynamically
    name_map = {
        "fund_house": ["fund_house", "fundHouse"],
        "scheme_category": ["scheme_category", "schemeCategory"],
        "scheme_type": ["scheme_type", "schemeType"],
    }

    for label, candidates in name_map.items():
        col = next((c for c in candidates if c in fund_master.columns), None)
        if col is None:
            logger.info("  Column '%s' not available in fund master.", label)
            continue
        uniques = fund_master[col].dropna().unique()
        logger.info("  Unique %s (%d):", label, len(uniques))
        for val in sorted(uniques)[:20]:  # cap to 20 for readability
            logger.info("    • %s", val)
        if len(uniques) > 20:
            logger.info("    … and %d more", len(uniques) - 20)

# ──────────────────────────────────────────────
# Main orchestration
# ──────────────────────────────────────────────


def main() -> None:
    """Entry-point: run the full Day 1 ETL pipeline."""
    start_time = time.time()
    logger.info("🚀 Starting Bluestock MF Capstone — Day 1 ETL Pipeline")

    # Step 1 — folder structure
    create_folder_structure()

    # Step 2 — fund master
    fund_master = fetch_fund_master()
    _rate_limit()

    # Step 3 — explore fund master
    explore_fund_master(fund_master)

    # Step 4 — NAV histories
    nav_frames: dict[int, pd.DataFrame] = {}
    for code in UNIQUE_SCHEME_CODES:
        try:
            nav_frames[code] = fetch_nav_history(code)
        except Exception:
            logger.exception("Failed to fetch NAV for scheme %d — skipping.", code)
            nav_frames[code] = pd.DataFrame(columns=["date", "nav"])
        _rate_limit()

    # Step 5 — combined NAV
    combined = build_combined_nav(nav_frames)

    # Step 6 — validate AMFI codes
    missing_codes = validate_amfi_codes(fund_master)

    # Step 7 — data quality report
    write_data_quality_report(fund_master, nav_frames, combined, missing_codes)

    elapsed = time.time() - start_time
    logger.info("✅ ETL Pipeline completed in %.1f seconds.", elapsed)


if __name__ == "__main__":
    main()
