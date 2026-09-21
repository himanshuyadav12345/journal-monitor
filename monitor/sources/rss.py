import feedparser
from dateutil import parser as dateparser
from monitor.models import Article
from monitor.normalize import normalize_doi

def _date(entry, names):
    for name in names:
        value = entry.get(name)
        if value:
            try: return dateparser.parse(value).isoformat()
            except Exception: pass
    return None

def fetch_rss(journal, url, source_label):
    feed = feedparser.parse(url)
    out=[]
    for entry in feed.entries:
        title=(entry.get("title") or "").strip()
        link=(entry.get("link") or "").strip()
        if not title or not link: continue
        doi=normalize_doi(entry.get("doi") or entry.get("dc_identifier") or entry.get("prism_doi") or "")
        out.append(Article(journal=journal["name"],journal_id=journal["id"],title=title,url=link,
            doi=doi or None,published=_date(entry,["published","created"]),
            updated=_date(entry,["updated"]),item_type=entry.get("type") or entry.get("dc_type"),
            source=source_label,issue=entry.get("issue") or entry.get("prism_issue")))
    return out
