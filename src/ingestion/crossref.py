from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from core.config import Settings

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
    """TODO(student): parse Crossref payload thanh list PaperRecord."""
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        paper_id = item.get("DOI", "")
        if not paper_id:
            continue
            
        titles = item.get("title", [])
        title = titles[0] if titles else ""
        
        abstract = item.get("abstract", "")
        abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()
        
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)
                
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""
        
        published = ""
        pub_date = item.get("published", {}).get("date-parts", [[]])[0]
        if len(pub_date) >= 3:
            published = f"{pub_date[0]:04d}-{pub_date[1]:02d}-{pub_date[2]:02d}"
            
        updated = item.get("created", {}).get("date-time", "")
        
        abs_url = item.get("URL", "")
        
        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=abstract,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url="",
            comment=""
        ))
        
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records."""
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,created,URL"
    }
    
    max_retries = 3
    payload = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code in (429, 503):
                logger.warning(f"Rate limited or unavailable. Retrying in {2 ** attempt}s...")
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.warning("All attempts failed. Will attempt to use local fallback snapshot.")
                break
            time.sleep(2 ** attempt)
            
    if not payload:
        fallback_path = settings.paths.raw_api_response
        if fallback_path.exists():
            logger.info(f"Loading from fallback snapshot: {fallback_path}")
            with open(fallback_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raise RuntimeError("Failed to fetch data from Crossref API and no local snapshot found")

    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    # Only write back if it's new data (not from fallback), but rewriting same data is fine
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    records = parse_crossref_payload(payload)
    
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump([vars(r) for r in records], f, ensure_ascii=False, indent=2)
        
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    if not path.exists():
        return []
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = []
    for item in data:
        records.append(PaperRecord(**item))
        
    return records
