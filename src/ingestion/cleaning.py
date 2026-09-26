from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from ingestion.crossref import PaperRecord

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_MIN_SUMMARY_CHARS = 20


def _clean_text(value: object) -> str:
    """Bo JATS/XML tag va chuan hoa khoang trang thua."""
    text = _TAG_RE.sub(" ", str(value or ""))
    return _WHITESPACE_RE.sub(" ", text).strip()


def _parse_date(value: object) -> pd.Timestamp | None:
    text = _clean_text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _format_date(value: pd.Timestamp | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d")


def build_text_for_embedding(row: pd.Series) -> str:
    """Ghep 5 phan ngu canh de embedding: title, authors, published, categories, summary."""
    authors = row["authors_joined"] or "Unknown"
    published = row["published"] or "Unknown"
    categories = row["categories_joined"] or "Uncategorized"
    return (
        f"Title: {row['title']}\n"
        f"Authors: {authors}\n"
        f"Published: {published}\n"
        f"Categories: {categories}\n"
        f"Summary: {row['summary']}"
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    - Chuan hoa title/summary (bo JATS tag, khoang trang thua).
    - Tinh `age_days = (run_date - published).days`.
    - Tao `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`.
    - Khu trung lap theo `paper_id` va loai bo dong thieu truong bat buoc.
    """
    if not records:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "age_days",
                "text_for_embedding",
            ]
        )

    run_ts = pd.Timestamp(run_date)
    if run_ts.tzinfo is None:
        run_ts = run_ts.tz_localize("UTC")

    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for record in records:
        paper_id = str(record.paper_id or "").strip()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)

        if not paper_id or not title or len(summary) < _MIN_SUMMARY_CHARS:
            continue
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        authors = [name for name in (_clean_text(author) for author in record.authors) if name]
        categories = [name for name in (_clean_text(cat) for cat in record.categories) if name]
        primary_category = _clean_text(record.primary_category) or (categories[0] if categories else "")

        published_ts = _parse_date(record.published)
        updated_ts = _parse_date(record.updated)
        age_days = pd.NA
        if published_ts is not None:
            age_days = int((run_ts - published_ts).days)

        row = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": primary_category,
            "published": _format_date(published_ts),
            "updated": updated_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if updated_ts is not None else "",
            "abs_url": str(record.abs_url or "").strip(),
            "pdf_url": str(record.pdf_url or "").strip(),
            "comment": _clean_text(record.comment),
            "authors_joined": ", ".join(authors),
            "categories_joined": ", ".join(categories) if categories else "Uncategorized",
            "summary_chars": len(summary),
            "age_days": age_days,
        }
        row["text_for_embedding"] = build_text_for_embedding(pd.Series(row))
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["age_days"] = pd.array(df["age_days"], dtype="Int64")
    df = df.sort_values(
        by=["published", "title"],
        ascending=[False, True],
        ignore_index=True,
    )
    return df
