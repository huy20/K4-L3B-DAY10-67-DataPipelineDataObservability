from datetime import datetime
import re
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str.strip()[:10], fmt)
        except ValueError:
            continue
    return None


def format_text_for_embedding(
    title: str,
    authors_joined: str,
    published: str,
    categories_joined: str,
    summary: str,
) -> str:
    """Tao text_for_embedding day du cau truc 5 phan."""
    return (
        f"Title: {title}\n"
        f"Authors: {authors_joined}\n"
        f"Published: {published}\n"
        f"Categories: {categories_joined}\n"
        f"Summary: {summary}"
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    ref_date = run_date.date() if isinstance(run_date, datetime) else run_date

    rows: list[dict[str, Any]] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id or "")
        raw_title = re.sub(r"<[^>]+>", " ", record.title or "")
        title = normalize_whitespace(raw_title)

        raw_summary = re.sub(r"<[^>]+>", " ", record.summary or "")
        summary = normalize_whitespace(raw_summary)

        authors = [normalize_whitespace(str(a)) for a in record.authors if a]
        authors = [a for a in authors if a]
        authors_joined = ", ".join(authors)

        categories = [normalize_whitespace(str(c)) for c in record.categories if c]
        categories = [c for c in categories if c]
        categories_joined = ", ".join(categories)
        primary_category = normalize_whitespace(record.primary_category or "")
        if not primary_category and categories:
            primary_category = categories[0]

        published = normalize_whitespace(record.published or "")
        updated = normalize_whitespace(record.updated or "") or published
        abs_url = normalize_whitespace(record.abs_url or "")
        pdf_url = normalize_whitespace(record.pdf_url or "") or abs_url
        comment = normalize_whitespace(record.comment or "")

        pub_dt = _parse_date(published)
        if pub_dt is not None:
            age_days = int((ref_date - pub_dt.date()).days)
        else:
            age_days = 0

        summary_chars = len(summary)
        text_for_embedding = format_text_for_embedding(
            title=title,
            authors_joined=authors_joined,
            published=published,
            categories_joined=categories_joined,
            summary=summary,
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Drop invalid rows (missing paper_id or title)
    df = df[
        df["paper_id"].astype(str).str.strip().ne("")
        & df["title"].astype(str).str.strip().ne("")
    ]

    # Drop duplicates
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort dataframe by published descending, then paper_id
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df

