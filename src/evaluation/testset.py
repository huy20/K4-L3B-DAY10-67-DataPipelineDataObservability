from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Tao bo evaluation set gom 10 cau hoi tu cleaned dataframe phu 4 nhom nghiep vu.

    4 nhom nghiep vu:
    1. summary (3 cau)
    2. authors (3 cau)
    3. date (2 cau)
    4. categories (2 cau)
    Tong: 10 cau hoi

    Moi row chua:
    - id
    - question_type
    - question
    - ground_truth
    - ground_truth_doc_ids
    """
    if len(df) < 10:
        raise ValueError(f"Dataframe must have at least 10 records to build test set, got {len(df)}")

    records = df.iloc[:10].to_dict(orient="records")
    test_set: list[dict[str, Any]] = []

    # 1. 3 cau hoi nhom summary
    for i in range(3):
        row = records[i]
        title = row["title"]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1:02d}",
                "question_type": "summary",
                "question": f"What is the summary of '{title}'?",
                "ground_truth": first_sentence(row["summary"]),
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    # 2. 3 cau hoi nhom authors
    for i in range(3, 6):
        row = records[i]
        title = row["title"]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1:02d}",
                "question_type": "authors",
                "question": f"Who authored the paper '{title}'?",
                "ground_truth": str(row["authors_joined"]),
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    # 3. 2 cau hoi nhom date
    for i in range(6, 8):
        row = records[i]
        title = row["title"]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1:02d}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": str(row["published"]),
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    # 4. 2 cau hoi nhom categories
    for i in range(8, 10):
        row = records[i]
        title = row["title"]
        test_set.append(
            {
                "id": f"q_{len(test_set) + 1:02d}",
                "question_type": "categories",
                "question": f"What categories are associated with the paper '{title}'?",
                "ground_truth": str(row["categories_joined"]),
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    if output_path:
        out_p = Path(output_path)
        write_json(out_p, test_set)
        # Đồng bộ thêm file golden_set.json trong cùng thư mục
        write_json(out_p.parent / "golden_set.json", test_set)

    return test_set
