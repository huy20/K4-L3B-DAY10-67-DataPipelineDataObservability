from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe gom 10 cau hoi qua 4 nhom nghiep vu:
    summary, authors, date, categories.

    1. Kiem tra so luong document toi thieu.
    2. Chon 10 paper dai dien.
    3. Tao 4 loai cau hoi:
       - summary (3 cau)
       - authors (3 cau)
       - date (2 cau)
       - categories (2 cau)
    4. Moi row co du:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    if len(df) < 10:
        raise ValueError(f"Dataframe must contain at least 10 rows to build test set, got {len(df)}")

    specs = [
        ("summary", "What is the summary of '{title}'?"),
        ("authors", "Who authored '{title}'?"),
        ("date", "When was '{title}' published?"),
        ("categories", "What categories does '{title}' belong to?"),
        ("summary", "What is the core focus of '{title}'?"),
        ("authors", "Who authored '{title}'?"),
        ("date", "When was '{title}' published?"),
        ("categories", "What categories does '{title}' belong to?"),
        ("summary", "Can you summarize '{title}'?"),
        ("authors", "Who authored '{title}'?"),
    ]

    test_set: list[dict[str, Any]] = []

    for index, (q_type, q_template) in enumerate(specs):
        row = df.iloc[index]
        title = str(row["title"]).strip()
        paper_id = str(row["paper_id"]).strip()

        question = q_template.format(title=title)

        if q_type == "summary":
            ground_truth = first_sentence(str(row["summary"])).strip()
        elif q_type == "authors":
            ground_truth = str(row["authors_joined"]).strip()
        elif q_type == "date":
            ground_truth = str(row["published"]).strip()
        elif q_type == "categories":
            ground_truth = str(row["categories_joined"]).strip()
        else:
            ground_truth = str(row.get("summary", "")).strip()

        test_set.append(
            {
                "id": f"eval-{index + 1:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    out_file = Path(output_path)
    write_json(out_file, test_set)
    return test_set

