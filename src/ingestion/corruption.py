from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, ensure_parent, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str | None = None) -> pd.DataFrame:
    """Simulate 6 dang data corruption theo yeu cau cua Checkpoint 4.

    1. Drop latest records (mat 20% ban ghi moi).
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate (< 8 ky tu).
    5. Lam published date cu di (vi pham Freshness SLA).
    6. Add duplicate rows (vi pham Unique ID).
    7. Rebuild text_for_embedding.
    8. Ghi corruption log vao output_log_path.
    """
    corrupted = df.copy()
    logs: list[dict[str, Any]] = []

    # 1. Drop 20% latest records
    n_drop = max(1, round(len(corrupted) * 0.20))
    dropped_ids = corrupted.iloc[:n_drop]["paper_id"].tolist()
    dropped_titles = corrupted.iloc[:n_drop]["title"].tolist()
    corrupted = corrupted.iloc[n_drop:].copy().reset_index(drop=True)
    logs.append(
        {
            "scenario": "drop_latest_records",
            "description": f"Dropped {n_drop} newest records ({n_drop/len(df)*100:.1f}%)",
            "count": n_drop,
            "dropped_paper_ids": dropped_ids,
            "dropped_titles": dropped_titles,
        }
    )

    # 2. Blank summary o mot so dong
    blank_indices = [0, 1] if len(corrupted) >= 2 else [0]
    for idx in blank_indices:
        corrupted.loc[idx, "summary"] = ""
        corrupted.loc[idx, "summary_chars"] = 0
    logs.append(
        {
            "scenario": "blank_summary",
            "description": "Erased abstract/summary on selected records",
            "affected_paper_ids": [corrupted.loc[i, "paper_id"] for i in blank_indices],
        }
    )

    # 3. Inject noise vao text summary
    noise_indices = [2, 3] if len(corrupted) >= 4 else []
    noise_payload = " [ERR_SYNTHETIC_CORRUPTION_GARBAGE_NOISE_###$$$@@@] "
    for idx in noise_indices:
        original = corrupted.loc[idx, "summary"]
        corrupted.loc[idx, "summary"] = f"{noise_payload} {original} {noise_payload}"
        corrupted.loc[idx, "summary_chars"] = len(corrupted.loc[idx, "summary"])
    logs.append(
        {
            "scenario": "inject_noise",
            "description": "Injected synthetic noise and garbage tokens into summary",
            "affected_paper_ids": [corrupted.loc[i, "paper_id"] for i in noise_indices],
        }
    )

    # 4. Truncate title (< 8 ky tu)
    truncate_indices = [4, 5] if len(corrupted) >= 6 else []
    for idx in truncate_indices:
        original_title = str(corrupted.loc[idx, "title"])
        corrupted.loc[idx, "title"] = original_title[:6].strip()
    logs.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated title to fewer than 8 characters to break exact lookup",
            "affected_paper_ids": [corrupted.loc[i, "paper_id"] for i in truncate_indices],
        }
    )

    # 5. Stale date (lui ngay xuat ban ve qua khu de vi pham Freshness SLA)
    # Lùi hơn 30% số bản ghi còn lại về năm 2020 (> 2000 ngày)
    stale_count = max(6, int(len(corrupted) * 0.35))
    stale_indices = list(range(len(corrupted) - stale_count, len(corrupted)))
    for idx in stale_indices:
        corrupted.loc[idx, "published"] = "2020-01-01"
        corrupted.loc[idx, "age_days"] = 2450
    logs.append(
        {
            "scenario": "stale_date",
            "description": f"Set publication date back to 2020 on {len(stale_indices)} records to violate Freshness SLA",
            "affected_paper_ids": [corrupted.loc[i, "paper_id"] for i in stale_indices],
        }
    )

    # 6. Duplicate rows (nhan ban du lieu de vi pham Unique ID)
    dup_rows = corrupted.iloc[[0, 1]].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    logs.append(
        {
            "scenario": "duplicate_rows",
            "description": "Duplicated rows to trigger uniqueness violation in Great Expectations",
            "duplicated_paper_ids": dup_rows["paper_id"].tolist(),
        }
    )

    # 7. Rebuild text_for_embedding va helper columns
    for idx in corrupted.index:
        title = str(corrupted.loc[idx, "title"])
        authors = corrupted.loc[idx, "authors"]
        if isinstance(authors, list):
            authors_joined = compact_join(authors, sep=", ")
        else:
            authors_joined = str(corrupted.loc[idx, "authors_joined"])
        corrupted.loc[idx, "authors_joined"] = authors_joined

        categories = corrupted.loc[idx, "categories"]
        if isinstance(categories, list):
            categories_joined = compact_join(categories, sep=", ")
        else:
            categories_joined = str(corrupted.loc[idx, "categories_joined"])
        corrupted.loc[idx, "categories_joined"] = categories_joined

        published = str(corrupted.loc[idx, "published"])
        summary = str(corrupted.loc[idx, "summary"])

        corrupted.loc[idx, "text_for_embedding"] = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

    # 8. Ghi corruption log
    corruption_payload = {
        "total_scenarios": len(logs),
        "initial_record_count": len(df),
        "corrupted_record_count": len(corrupted),
        "scenarios": logs,
    }

    if output_log_path:
        write_json(Path(output_log_path), corruption_payload)

    return corrupted
