import json
import os
from pathlib import Path

from monitor.notion_sync import (
    DATA_SOURCE_ID,
    JOURNAL_DIRECTORY_DATA_SOURCE_ID,
    _property_text,
    _request,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "journal_link_backfill_dry_run.json"


def normalize(value):
    return (value or "").strip().casefold()


def query_all(token, data_source_id):
    pages = []
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = _request(
            token,
            "POST",
            f"/data_sources/{data_source_id}/query",
            json=body,
        )
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            return pages
        cursor = data.get("next_cursor")
        if not cursor:
            return pages


def journal_name(page):
    props = page.get("properties", {})
    return _property_text(
        props.get("Journal") or props.get("Name") or props.get("title")
    ).strip()


def article_identifier(page):
    props = page.get("properties", {})
    return {
        "page_id": page.get("id"),
        "doi": _property_text(props.get("DOI")).strip(),
        "title": _property_text(props.get("Title")).strip(),
        "journal": _property_text(props.get("Journal")).strip(),
    }


def has_journal_link(page):
    prop = page.get("properties", {}).get("Journal Link")
    if not prop:
        return False
    if prop.get("type") == "relation":
        return bool(prop.get("relation"))
    return False


def main():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN is not set")

    directory_pages = query_all(token, JOURNAL_DIRECTORY_DATA_SOURCE_ID)
    articles = query_all(token, DATA_SOURCE_ID)

    directory = {}
    duplicate_directory_names = {}
    for page in directory_pages:
        name = journal_name(page)
        key = normalize(name)
        if not key:
            continue
        if key in directory:
            duplicate_directory_names.setdefault(key, [directory[key]]).append(page.get("id"))
        else:
            directory[key] = page.get("id")

    summary = {
        "mode": "dry-run",
        "writes_performed": 0,
        "article_pages_examined": len(articles),
        "already_linked": 0,
        "exact_matches": 0,
        "unmatched": 0,
        "ambiguous": 0,
        "potential_updates": 0,
        "directory_pages_examined": len(directory_pages),
        "directory_duplicate_names": len(duplicate_directory_names),
    }

    results = []
    for page in articles:
        item = article_identifier(page)
        if has_journal_link(page):
            summary["already_linked"] += 1
            results.append({**item, "status": "already_linked", "matched_directory_page_id": None})
            continue

        key = normalize(item["journal"])
        matches = []
        if key in directory:
            matches = [directory[key]]
            if key in duplicate_directory_names:
                matches = duplicate_directory_names[key]

        if len(matches) == 1:
            summary["exact_matches"] += 1
            summary["potential_updates"] += 1
            results.append({
                **item,
                "status": "exact_match",
                "matched_directory_page_id": matches[0],
            })
        elif len(matches) == 0:
            summary["unmatched"] += 1
            results.append({
                **item,
                "status": "unmatched",
                "matched_directory_page_id": None,
            })
        else:
            summary["ambiguous"] += 1
            results.append({
                **item,
                "status": "ambiguous",
                "matched_directory_page_id": None,
                "candidate_directory_page_ids": matches,
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Historical Journal Link Backfill — DRY RUN")
    for key in (
        "article_pages_examined",
        "already_linked",
        "exact_matches",
        "unmatched",
        "ambiguous",
        "potential_updates",
        "directory_pages_examined",
        "directory_duplicate_names",
        "writes_performed",
    ):
        print(f"{key}: {summary[key]}")


if __name__ == "__main__":
    main()
