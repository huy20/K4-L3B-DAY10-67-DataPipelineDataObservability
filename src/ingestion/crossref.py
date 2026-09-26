from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any
import urllib.parse
import urllib.request

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_jats_tags(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    message = payload.get("message", {})
    items = message.get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "")
        if not doi:
            continue

        raw_title = item.get("title", [""])
        if isinstance(raw_title, list):
            title = _clean_jats_tags(raw_title[0]) if raw_title else ""
        else:
            title = _clean_jats_tags(str(raw_title))

        raw_abstract = item.get("abstract", "")
        summary = _clean_jats_tags(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)

        categories: list[str] = [cat.strip() for cat in item.get("subject", []) if cat.strip()]
        primary_category = categories[0] if categories else "General"

        date_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if len(date_parts) >= 3:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-{date_parts[2]:02d}"
        elif len(date_parts) == 2:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-01"
        elif len(date_parts) == 1:
            published = f"{date_parts[0]:04d}-01-01"
        else:
            published = ""

        created = item.get("created", {}).get("date-time", "")
        updated = created[:10] if created else published

        url = item.get("URL", f"https://doi.org/{doi}")

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=f"Crossref record {doi}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records."""
    if settings.refresh_source:
        query_params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        encoded_query = urllib.parse.urlencode(query_params)
        url = f"https://api.crossref.org/works?{encoded_query}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "CrossrefIngestionBot/1.0 (mailto:student@example.com)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    write_json(settings.paths.raw_api_response, payload)
                    records = parse_crossref_payload(payload)
                    write_json(
                        settings.paths.raw_records_json,
                        [asdict(record) for record in records],
                    )
                    return records
        except Exception:
            # Fallback to local snapshot if network error or rate limit occurs
            pass

    # Read from local snapshot if exists
    if settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    if settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
        records = parse_crossref_payload(payload)
        write_json(
            settings.paths.raw_records_json,
            [asdict(record) for record in records],
        )
        return records

    return []


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=item.get("primary_category", ""),
                published=item.get("published", ""),
                updated=item.get("updated", ""),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    return records
