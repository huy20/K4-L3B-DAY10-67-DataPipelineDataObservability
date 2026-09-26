from pathlib import Path

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import format_text_for_embedding


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate 6 dang data corruption theo yeu cau cua lab:
    1. Drop latest records: Mat ~25% ban ghi moi nhat.
    2. Blank summary: Xoa rong tom tat o mot so dong.
    3. Inject noise: Chen chuoi ky tu rac vao tom tat.
    4. Truncate title: Cat ngan tieu de xuong < 8 ky tu.
    5. Stale date: Lui ngay xuat ban ve qua khu de vi pham Freshness SLA.
    6. Duplicate rows: Nhan ban ban ghi gay vi pham uniqueness.
    7. Rebuild text_for_embedding va summary_chars.
    8. Ghi corruption log chi tiet vao output_log_path.
    """
    corrupted = df.copy()

    # 1. Drop latest records (~25% ban ghi moi nhat)
    drop_count = max(1, int(len(df) * 0.25))
    dropped_ids = list(corrupted.iloc[:drop_count]["paper_id"])
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)

    # 2. Blank summary (xoa rong tom tat)
    blank_ids = list(corrupted.iloc[:2]["paper_id"])
    for i in range(min(2, len(corrupted))):
        corrupted.at[i, "summary"] = ""

    # 3. Inject noise (chen chuoi rac)
    noise_ids = list(corrupted.iloc[2:4]["paper_id"])
    for i in range(2, min(4, len(corrupted))):
        corrupted.at[i, "summary"] = (
            "###CORRUPTED_TEXT_NOISE_GARBAGE### " * 8
            + str(corrupted.at[i, "summary"])
        )

    # 4. Truncate title (cat ngan tieu de < 8 ky tu)
    trunc_ids = list(corrupted.iloc[4:6]["paper_id"])
    for i in range(4, min(6, len(corrupted))):
        corrupted.at[i, "title"] = str(corrupted.at[i, "title"])[:5]

    # 5. Stale date (lui ngay xuat ban ve qua khu de vi pham Freshness SLA > 180 ngay)
    stale_count = min(14, len(corrupted))
    stale_ids = list(corrupted.iloc[6:stale_count]["paper_id"])
    for i in range(6, stale_count):
        corrupted.at[i, "published"] = "2020-01-01"
        corrupted.at[i, "age_days"] = 2400

    # 6. Duplicate rows (nhan ban ban ghi de gay vi pham uniqueness)
    dup_rows = corrupted.iloc[:1].copy()
    dup_ids = list(dup_rows["paper_id"])
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)

    # 7. Rebuild text_for_embedding va summary_chars
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = [
        format_text_for_embedding(
            title=str(row["title"]),
            authors_joined=str(row["authors_joined"]),
            published=str(row["published"]),
            categories_joined=str(row["categories_joined"]),
            summary=str(row["summary"]),
        )
        for _, row in corrupted.iterrows()
    ]

    # 8. Ghi corruption log chi tiet
    corruption_log = {
        "original_row_count": len(df),
        "corrupted_row_count": len(corrupted),
        "scenarios": [
            {
                "scenario": "drop_latest_records",
                "description": f"Dropped {drop_count} latest published records (~{round(drop_count / len(df) * 100, 1)}%)",
                "count": len(dropped_ids),
                "affected_paper_ids": dropped_ids,
            },
            {
                "scenario": "blank_summary",
                "description": "Erased abstract/summary for selected records (< 20 chars violation)",
                "count": len(blank_ids),
                "affected_paper_ids": blank_ids,
            },
            {
                "scenario": "inject_noise",
                "description": "Injected repetitive text noise and garbage prefixes into summaries",
                "count": len(noise_ids),
                "affected_paper_ids": noise_ids,
            },
            {
                "scenario": "truncate_title",
                "description": "Truncated paper title to 5 characters (< 8 chars violation)",
                "count": len(trunc_ids),
                "affected_paper_ids": trunc_ids,
            },
            {
                "scenario": "stale_date",
                "description": "Rolled publication date back to 2020-01-01 (age_days=2400), violating Freshness SLA (>180 days)",
                "count": len(stale_ids),
                "affected_paper_ids": stale_ids,
            },
            {
                "scenario": "duplicate_rows",
                "description": "Appended duplicate rows causing primary key uniqueness constraint violation",
                "count": len(dup_ids),
                "affected_paper_ids": dup_ids,
            },
        ],
    }

    out_file = Path(output_log_path)
    write_json(out_file, corruption_log)
    return corrupted

