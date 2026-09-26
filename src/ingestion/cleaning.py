from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days = (run_date - published).days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding (cau truc 5 phan: Title, Authors, Published, Categories, Summary)
    5. Drop duplicates theo paper_id va filter row xau.
    6. Sort dataframe va return.
    """
    rows: list[dict[str, Any]] = []

    if run_date.tzinfo is None:
        run_dt = run_date.replace(tzinfo=timezone.utc)
    else:
        run_dt = run_date.astimezone(timezone.utc)

    for record in records:
        paper_id = record.paper_id.strip()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)

        authors = [_clean_text(a) for a in record.authors if _clean_text(a)]
        categories = [_clean_text(c) for c in record.categories if _clean_text(c)]
        primary_category = _clean_text(record.primary_category) or (categories[0] if categories else "General")

        published_str = record.published.strip()
        age_days = 0
        if published_str:
            try:
                pub_dt = pd.to_datetime(published_str)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.tz_localize(timezone.utc)
                else:
                    pub_dt = pub_dt.tz_convert(timezone.utc)
                age_days = (run_dt - pub_dt).days
            except Exception:
                age_days = 0

        authors_joined = compact_join(authors, sep=", ")
        categories_joined = compact_join(categories, sep=", ")
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published_str,
                "updated": record.updated.strip(),
                "abs_url": record.abs_url.strip(),
                "pdf_url": record.pdf_url.strip(),
                "comment": record.comment.strip(),
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Drop duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Filter rows with missing or empty key fields
    df = df[
        (df["paper_id"].str.len() > 0)
        & (df["title"].str.len() > 0)
        & (df["summary"].str.len() > 0)
    ]

    # Sort by published date descending and reset index
    df = df.sort_values(by=["published"], ascending=False).reset_index(drop=True)
    return df
