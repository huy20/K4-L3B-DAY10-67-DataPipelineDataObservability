from __future__ import annotations

import random

import pandas as pd

from core.utils import now_utc, write_json
from ingestion.cleaning import build_text_for_embedding

_SEED = 42
_DROP_RATIO = 0.20
_BLANK_SUMMARY_RATIO = 0.20
_INJECT_NOISE_RATIO = 0.20
_TRUNCATE_TITLE_RATIO = 0.15
_STALE_DATE_RATIO = 0.20
_DUPLICATE_ROWS_RATIO = 0.15
_STALE_PUBLISHED = "2024-01-01"
_TRUNCATED_TITLE_LENGTH = 6
_NOISE_TOKENS = " \u0000\u00a7###!!! ???<<<noise>>>"


def _pick_indices(frame: pd.DataFrame, ratio: float, rng: random.Random) -> list[int]:
    count = max(1, int(round(len(frame) * ratio)))
    count = min(count, len(frame))
    return sorted(rng.sample(list(frame.index), count))


def _scenario(
    name: str,
    description: str,
    parameters: dict,
    affected: list[int],
    paper_ids: list[str],
) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "rows_affected": len(affected),
        "paper_ids": paper_ids,
    }


def _rebuild_derived_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Cap nhat lai cac cot dan xuat sau khi corruption thay doi input."""
    frame = frame.copy()
    frame["summary_chars"] = frame["summary"].astype(str).str.len()
    frame["text_for_embedding"] = frame.apply(build_text_for_embedding, axis=1)
    run_ts = pd.Timestamp(now_utc())
    published_ts = pd.to_datetime(frame["published"], errors="coerce", utc=True)
    frame["age_days"] = pd.array((run_ts - published_ts).dt.days, dtype="Int64")
    return frame


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Tiem 6 kich ban lam ban du lieu va ghi corruption log.

    1. drop_latest_records  - mat 20% ban ghi moi nhat.
    2. blank_summary        - xoa rong tom tat.
    3. inject_noise         - chen ky tu rac vao tom tat.
    4. truncate_title       - cat tieu de con < 8 ky tu.
    5. stale_date           - lui ngay xuat ban ve qua khu (age_days > 180).
    6. duplicate_rows       - nhan ban ban ghi.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    rng = random.Random(_SEED)
    original = df.reset_index(drop=True).copy()
    work = original.copy()
    scenarios: list[dict] = []

    # 1. Drop latest records.
    ordered_index = work.sort_values("published", ascending=False, kind="stable").index.tolist()
    drop_count = min(len(work), max(1, int(round(len(work) * _DROP_RATIO))))
    drop_index = ordered_index[:drop_count]
    drop_ids = work.loc[drop_index, "paper_id"].astype(str).tolist()
    work = work.drop(index=drop_index).reset_index(drop=True)
    scenarios.append(
        _scenario(
            "drop_latest_records",
            "Remove the newest records; simulates missing fresh data in the index.",
            {"ratio": _DROP_RATIO, "count": drop_count},
            drop_index,
            drop_ids,
        )
    )

    # 2. Blank summary.
    blank_index = _pick_indices(work, _BLANK_SUMMARY_RATIO, rng)
    blank_ids = work.loc[blank_index, "paper_id"].astype(str).tolist()
    work.loc[blank_index, "summary"] = ""
    scenarios.append(
        _scenario(
            "blank_summary",
            "Replace summary with an empty string; simulates an upstream extraction failure.",
            {"ratio": _BLANK_SUMMARY_RATIO},
            blank_index,
            blank_ids,
        )
    )

    # 3. Inject noise into summary.
    noise_index = _pick_indices(work, _INJECT_NOISE_RATIO, rng)
    noise_ids = work.loc[noise_index, "paper_id"].astype(str).tolist()
    for index in noise_index:
        work.at[index, "summary"] = f"{work.at[index, 'summary']}{_NOISE_TOKENS}"
    scenarios.append(
        _scenario(
            "inject_noise",
            "Append junk characters to the summary; simulates parsing/encoding noise.",
            {"ratio": _INJECT_NOISE_RATIO, "tokens": _NOISE_TOKENS.strip()},
            noise_index,
            noise_ids,
        )
    )

    # 4. Truncate title.
    truncate_index = _pick_indices(work, _TRUNCATE_TITLE_RATIO, rng)
    truncate_ids = work.loc[truncate_index, "paper_id"].astype(str).tolist()
    for index in truncate_index:
        work.at[index, "title"] = str(work.at[index, "title"])[:_TRUNCATED_TITLE_LENGTH]
    scenarios.append(
        _scenario(
            "truncate_title",
            "Cut titles shorter than 8 characters; breaks exact-title lookup and embedding context.",
            {"ratio": _TRUNCATE_TITLE_RATIO, "max_length": _TRUNCATED_TITLE_LENGTH},
            truncate_index,
            truncate_ids,
        )
    )

    # 5. Stale date.
    stale_index = _pick_indices(work, _STALE_DATE_RATIO, rng)
    stale_ids = work.loc[stale_index, "paper_id"].astype(str).tolist()
    work.loc[stale_index, "published"] = _STALE_PUBLISHED
    scenarios.append(
        _scenario(
            "stale_date",
            "Push the publication date far into the past; violates the freshness SLA.",
            {"ratio": _STALE_DATE_RATIO, "published": _STALE_PUBLISHED},
            stale_index,
            stale_ids,
        )
    )

    work = _rebuild_derived_columns(work)

    # 6. Duplicate rows.
    duplicate_index = _pick_indices(work, _DUPLICATE_ROWS_RATIO, rng)
    duplicate_ids = work.loc[duplicate_index, "paper_id"].astype(str).tolist()
    duplicated = work.loc[duplicate_index].copy()
    work = pd.concat([work, duplicated], ignore_index=True)
    work = _rebuild_derived_columns(work)
    scenarios.append(
        _scenario(
            "duplicate_rows",
            "Append duplicated records; breaks the paper_id uniqueness contract.",
            {"ratio": _DUPLICATE_ROWS_RATIO},
            duplicate_index,
            duplicate_ids,
        )
    )

    log = {
        "seed": _SEED,
        "generated_at": now_utc().isoformat(),
        "total_rows_before": int(len(original)),
        "total_rows_after": int(len(work)),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }
    write_json(output_log_path, log)
    return work
