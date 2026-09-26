from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json

_STALE_RATIO_LIMIT = 0.25
_MIN_ROWS = 1
_MAX_ROWS = 10_000
_MIN_SUMMARY_CHARS = 20
_MAX_SUMMARY_CHARS = 20_000


def _quality_report_path(settings: Settings, report_name: str):
    mapping = {
        "baseline": settings.paths.baseline_quality_report,
        "corrupted": settings.paths.corrupted_quality_report,
        "repaired": settings.paths.quality_dir / "repaired_quality_report.json",
        "test": settings.paths.quality_dir / "test_quality_report.json",
    }
    return mapping.get(report_name, settings.paths.quality_dir / f"{report_name}_quality_report.json")


def _build_suite() -> gx.ExpectationSuite:
    """4 expectations thiet yeu cua GX 1.x."""
    suite = gx.ExpectationSuite(name="papers_quality_suite")
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=_MIN_ROWS, max_value=_MAX_ROWS)
    )
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="summary",
            min_value=_MIN_SUMMARY_CHARS,
            max_value=_MAX_SUMMARY_CHARS,
        )
    )
    return suite


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    threshold = settings.freshness_threshold_days
    total_rows = int(len(df))

    published = df["published"].astype(str).str.strip() if "published" in df.columns else pd.Series(dtype=str)
    valid_published = published[published != ""]
    latest_published = valid_published.max() if not valid_published.empty else None
    oldest_published = valid_published.min() if not valid_published.empty else None

    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
    else:
        ages = pd.Series(dtype="float64")

    stale_rows = int((ages > threshold).sum())
    unknown_rows = int(ages.isna().sum())
    stale_ratio = (stale_rows / total_rows) if total_rows else 0.0
    is_fresh = bool(total_rows > 0 and stale_ratio <= _STALE_RATIO_LIMIT)

    return {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "unknown_published_rows": unknown_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report va ghi JSON ra report_path."""
    payload = _freshness_payload(df, settings)
    write_json(report_path, payload)
    return payload


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay Great Expectations 1.x suite + freshness SLA va ghi report JSON."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = _build_suite()
    result = batch.validate(suite)

    expectations: list[dict[str, Any]] = []
    for item in result.results:
        config = item.expectation_config
        observed = None
        if item.result:
            observed = item.result.get("observed_value")
        expectations.append(
            {
                "expectation_type": config.type,
                "column": config.kwargs.get("column"),
                "success": bool(item.success),
                "observed_value": observed,
            }
        )

    freshness = _freshness_payload(df, settings)
    payload: dict[str, Any] = {
        "report_name": report_name,
        "success": bool(result.success),
        "row_count": int(len(df)),
        "expectations": expectations,
        "freshness": freshness,
        "is_fresh": freshness["is_fresh"],
        "stale_rows": freshness["stale_rows"],
    }

    suite_path = settings.paths.gx_dir / f"{report_name}_suite.json"
    ensure_parent(suite_path)
    write_json(suite_path, suite.to_json_dict())
    write_json(_quality_report_path(settings, report_name), payload)
    return payload
