from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

_QUESTION_PLAN: list[tuple[str, int]] = [
    ("summary", 3),
    ("authors", 3),
    ("date", 2),
    ("categories", 2),
]


def _build_question(row: pd.Series, question_type: str) -> dict[str, Any]:
    title = str(row["title"]).strip()
    if question_type == "summary":
        question = f"Summarize the paper titled '{title}'."
        ground_truth = first_sentence(str(row["summary"]))
    elif question_type == "authors":
        question = f"Who authored the paper titled '{title}'?"
        ground_truth = str(row["authors_joined"])
    elif question_type == "date":
        question = f"When was the paper titled '{title}' published?"
        ground_truth = str(row["published"])
    elif question_type == "categories":
        question = f"What categories are associated with the paper titled '{title}'?"
        ground_truth = str(row["categories_joined"])
    else:  # pragma: no cover - guard for invalid config
        raise ValueError(f"Unsupported question type: {question_type}")

    return {
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth.strip(),
        "ground_truth_doc_ids": [str(row["paper_id"])],
    }


def _take(pool: list[int], count: int, used: set[int]) -> list[int]:
    picked: list[int] = []
    for index in pool:
        if len(picked) == count:
            break
        if index in used:
            continue
        used.add(index)
        picked.append(index)
    return picked


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set 10 cau hoi qua 4 nhom: summary, authors, date, categories."""
    total_needed = sum(count for _, count in _QUESTION_PLAN)
    if len(df) < total_needed:
        raise ValueError(
            f"Can it nhat {total_needed} tai lieu sach de sinh test set, hien co {len(df)}."
        )

    frame = df.reset_index(drop=True)
    all_indices = list(range(len(frame)))
    dated_indices = [
        index
        for index in all_indices
        if str(frame.iloc[index]["published"]).strip() not in {"", "nan", "NaT"}
    ]

    used: set[int] = set()
    questions: list[dict[str, Any]] = []

    for question_type, count in _QUESTION_PLAN:
        pool = dated_indices if question_type == "date" else all_indices
        if len(pool) < count:
            pool = all_indices
        for index in _take(pool, count, used):
            questions.append(_build_question(frame.iloc[index], question_type))

    for position, item in enumerate(questions, start=1):
        item["id"] = f"q-{position:03d}"

    write_json(output_path, questions)
    return questions
