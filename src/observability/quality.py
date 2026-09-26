from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


class QualityReport(dict):
    """Dictionary supporting attribute access."""

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    """Chay kiem dinh chat luong du lieu bang Great Expectations 1.x va Freshness SLA.

    1. Khoi tao ephemeral context GX 1.x
    2. Dinh nghia Pandas data source, dataframe asset, whole dataframe batch definition
    3. Dinh nghia 4 Expectations thiet yeu:
       - ExpectTableRowCountToBeBetween
       - ExpectColumnValuesToNotBeNull
       - ExpectColumnValuesToBeUnique
       - ExpectColumnValueLengthsToBeBetween
    4. Tinh toan Freshness SLA: is_fresh = False neu ty le age_days > 180 vuot 25%
    5. Ghi ket qua vao data/quality/
    """
    # 1. Ephemeral context theo chuan GX 1.x
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Dinh nghia 4 Expectations thiet yeu
    suite = gx.ExpectationSuite(name=f"papers_suite_{report_name}")
    suite.add_expectation(ExpectTableRowCountToBeBetween(min_value=1, max_value=1000))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(
        ExpectColumnValueLengthsToBeBetween(
            column="summary",
            min_value=10,
            max_value=5000,
        )
    )

    # 3. Chay validation
    validation_result = batch.validate(suite)
    gx_success = bool(validation_result.success)

    # 4. Tinh toan Freshness SLA
    total_rows = len(df)
    threshold_days = settings.freshness_threshold_days
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > threshold_days).sum())
    else:
        stale_rows = 0
    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    # Overall success phai thoa man ca GX expectation va Freshness SLA
    overall_success = bool(gx_success and is_fresh)

    quality_report = QualityReport({
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": is_fresh,
        "total_rows": total_rows,
        "freshness": {
            "stale_rows": stale_rows,
            "stale_ratio": round(stale_ratio, 4),
            "threshold_days": threshold_days,
            "is_fresh": is_fresh,
        },
        "expectations": validation_result.to_json_dict(),
    })

    # 5. Ghi ket qua vao data/quality/
    if report_name == "baseline":
        output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        output_path = settings.paths.corrupted_quality_report
    else:
        output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    write_json(output_path, quality_report)
    return quality_report


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Tong hop freshness report theo SLA."""
    total_rows = len(df)
    threshold_days = settings.freshness_threshold_days

    published_series = (
        df["published"].dropna().astype(str)
        if "published" in df.columns
        else pd.Series([], dtype=str)
    )
    latest_published = str(published_series.max()) if not published_series.empty else ""
    oldest_published = str(published_series.min()) if not published_series.empty else ""

    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > threshold_days).sum())
    else:
        stale_rows = 0

    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": threshold_days,
        "max_allowed_stale_ratio": 0.25,
        "is_fresh": is_fresh,
    }

    target = Path(report_path) if report_path else settings.paths.freshness_report
    write_json(target, payload)
    return payload
