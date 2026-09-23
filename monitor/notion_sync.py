import os
import time
from datetime import datetime, timezone
import requests

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
DATA_SOURCE_ID = os.getenv(
    "NOTION_DATA_SOURCE_ID",
    "3e264599-6a8c-80a0-9550-000b851d0067",
)
JOURNAL_DIRECTORY_DATA_SOURCE_ID = os.getenv(
    "NOTION_JOURNAL_DIRECTORY_DATA_SOURCE_ID",
    "3cfd4973-125b-4cf9-ac1c-0163e7d7fec1",
)


class NotionSyncError(RuntimeError):
    pass


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _request(token, method, path, **kwargs):
    url = f"{API_BASE}{path}"
    for attempt in range(6):
        r = requests.request(method, url, headers=_headers(token), timeout=60, **kwargs)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else min(2 ** attempt, 30)
            time.sleep(delay)
            continue
        if r.status_code >= 500:
            time.sleep(min(2 ** attempt, 30))
            continue
        if not r.ok:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise NotionSyncError(f"Notion API {r.status_code}: {detail}")
        return r.json()
    raise NotionSyncError(f"Notion API request failed after retries: {method} {path}")


def _text(value):
    if not value:
        return ""
    return value[0].get("plain_text", "") if isinstance(value, list) else ""


def _property_text(prop):
    if not prop:
        return ""
    if prop.get("type") == "title":
        return _text(prop.get("title"))
    if prop.get("type") == "rich_text":
        return _text(prop.get("rich_text"))
    if prop.get("type") == "url":
        return prop.get("url") or ""
    return ""


def _existing_keys(token):
    keys = set()
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = _request(
            token,
            "POST",
            f"/data_sources/{DATA_SOURCE_ID}/query",
            json=body,
        )
        for page in data.get("results", []):
            props = page.get("properties", {})
            doi = _property_text(props.get("DOI")).strip().lower()
            url = _property_text(props.get("userDefined:URL") or props.get("URL")).strip()
            title = _property_text(props.get("Title")).strip().lower()
            if doi:
                keys.add(("doi", doi))
            if url:
                keys.add(("url", url))
            if title:
                keys.add(("title", title))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return keys


def _rich_text(value):
    value = (value or "")[:2000]
    return {"rich_text": [{"type": "text", "text": {"content": value}}]} if value else {"rich_text": []}


def _title(value):
    value = (value or "")[:2000]
    return {"title": [{"type": "text", "text": {"content": value}}]}


def _date(value):
    if not value:
        return None
    return {"date": {"start": value[:10]}}


def _as_dict(article):
    if isinstance(article, dict):
        return article
    if hasattr(article, "to_dict"):
        return article.to_dict()
    raise TypeError(f"Unsupported article type: {type(article).__name__}")


def _journal_directory_pages(token):
    """Return {journal name: Notion page id} for the Journal Directory."""
    mapping = {}
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = _request(
            token,
            "POST",
            f"/data_sources/{JOURNAL_DIRECTORY_DATA_SOURCE_ID}/query",
            json=body,
        )
        for page in data.get("results", []):
            props = page.get("properties", {})
            name = _property_text(
                props.get("Journal") or props.get("Name") or props.get("title")
            ).strip()
            if name:
                mapping[name.casefold()] = page.get("id")
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return mapping


def _page_payload(article, journal_page_id=None):
    article = _as_dict(article)
    properties = {
        "Title": _title(article.get("title")),
        "Journal": _rich_text(article.get("journal")),
        "Item Type": _rich_text(article.get("item_type")),
        "Issue": _rich_text(article.get("issue")),
        "DOI": _rich_text(article.get("doi")),
        "Source": _rich_text(article.get("source")),
        "Stage": {"select": {"name": "Online First" if article.get("stage") == "online_first" else "Issue"}},
        "URL": {"url": article.get("url")} if article.get("url") else {"url": None},
    }
    if journal_page_id:
        properties["Journal Link"] = {"relation": [{"id": journal_page_id}]}
    published = _date(article.get("published"))
    detected = _date(article.get("detected") or datetime.now(timezone.utc).date().isoformat())
    if published:
        properties["Published"] = published
    if detected:
        properties["Detected"] = detected
    return {
        "parent": {
            "type": "data_source_id",
            "data_source_id": DATA_SOURCE_ID,
        },
        "properties": properties,
    }


def sync_articles(articles):
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise NotionSyncError("NOTION_TOKEN is not set")

    if not articles:
        print("Notion sync: nothing to add.")
        return 0

    existing = _existing_keys(token)
    journal_pages = _journal_directory_pages(token)
    added = 0
    skipped = 0

    for raw_article in articles:
        article = _as_dict(raw_article)
        doi = (article.get("doi") or "").strip().lower()
        url = (article.get("url") or "").strip()
        title = (article.get("title") or "").strip().lower()
        candidate_keys = []
        if doi:
            candidate_keys.append(("doi", doi))
        if url:
            candidate_keys.append(("url", url))
        if title:
            candidate_keys.append(("title", title))

        if any(key in existing for key in candidate_keys):
            skipped += 1
            continue

        journal_name = (article.get("journal") or "").strip().casefold()
        journal_page_id = journal_pages.get(journal_name)
        if not journal_page_id:
            raise NotionSyncError(
                f"Journal Directory entry not found for journal: {article.get('journal')!r}"
            )

        _request(token, "POST", "/pages", json=_page_payload(article, journal_page_id))
        for key in candidate_keys:
            existing.add(key)
        added += 1
        time.sleep(0.4)

    print(f"Notion sync: added {added}, skipped {skipped} existing records.")
    return added
