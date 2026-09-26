import logging
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        raw_title = item.get("title", "")
        if isinstance(raw_title, list):
            raw_title = raw_title[0] if raw_title else ""
        title = normalize_whitespace(str(raw_title))

        raw_abstract = item.get("abstract", "")
        clean_abstract = re.sub(r"<[^>]+>", " ", str(raw_abstract))
        summary = normalize_whitespace(clean_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = normalize_whitespace(f"{given} {family}".strip())
            if full_name:
                authors.append(full_name)

        categories = [
            normalize_whitespace(str(c))
            for c in item.get("subject", [])
            if c
        ]
        primary_category = categories[0] if categories else ""

        pub_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if len(pub_parts) >= 3:
            pub_str = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-{pub_parts[2]:02d}"
        elif len(pub_parts) == 2:
            pub_str = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-01"
        elif len(pub_parts) == 1:
            pub_str = f"{pub_parts[0]:04d}-01-01"
        else:
            pub_str = ""

        updated = pub_str
        url = item.get("URL", "").strip() or f"https://doi.org/{doi}"
        comment = f"Crossref record {doi}"

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=pub_str,
            updated=updated,
            abs_url=url,
            pdf_url=url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.
    Co co che retry va fallback snapshot local khi offline hoac 429/503.
    """
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    if not settings.refresh_source and raw_response_path.exists():
        payload = read_json(raw_response_path)
        records = parse_crossref_payload(payload)
        write_json(raw_records_path, [asdict(r) for r in records])
        return records

    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "DataObservabilityLab/1.0 (mailto:student@vinuni.edu.vn)"
    }

    payload = None
    retries = 3
    backoff = 1.0

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                payload = response.json()
                break
            elif response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(backoff)
                backoff *= 2
            else:
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Attempt %d to fetch Crossref failed: %s", attempt + 1, exc)
            if attempt == retries - 1:
                break
            time.sleep(backoff)
            backoff *= 2

    if payload is not None and "message" in payload:
        write_json(raw_response_path, payload)
        records = parse_crossref_payload(payload)
        write_json(raw_records_path, [asdict(r) for r in records])
        return records

    # Fallback ve local snapshot khi offline hoac loi mang/rate-limit
    if raw_response_path.exists():
        logger.info("Using local raw response snapshot fallback at %s", raw_response_path)
        payload = read_json(raw_response_path)
        records = parse_crossref_payload(payload)
        write_json(raw_records_path, [asdict(r) for r in records])
        return records

    if raw_records_path.exists():
        logger.info("Using local raw records snapshot fallback at %s", raw_records_path)
        return load_raw_records(raw_records_path)

    raise RuntimeError(
        f"Unable to fetch from Crossref API and no local snapshot found at {raw_response_path}"
    )


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh list `PaperRecord`."""
    data = read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected list of records in {path}, got {type(data)}")
    return [PaperRecord(**item) for item in data]
