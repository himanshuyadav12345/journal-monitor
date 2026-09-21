import re
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

def _norm(value):
    value=(value or "").lower()
    value=re.sub(r"[^a-z0-9]+"," ",value)
    return " ".join(value.split())

def _feed_matches_journal(feed_title, journal_name):
    if not feed_title:
        return True
    feed=_norm(feed_title)
    journal=_norm(journal_name)
    if not feed or not journal:
        return True
    if feed == journal or journal in feed or feed in journal:
        return True
    stop={"the","a","an","of","and","in","on","for","journal","review","history","studies"}
    ft={x for x in feed.split() if x not in stop}
    jt={x for x in journal.split() if x not in stop}
    if not ft or not jt:
        return True
    return len(ft & jt) >= min(2,len(jt))

def fetch_rss(journal, url, source_label):
    feed = feedparser.parse(url)
    if getattr(feed,"bozo",False) and not feed.entries:
        return []
    feed_title=(feed.feed.get("title") or "").strip()
    if not _feed_matches_journal(feed_title,journal["name"]):
        return []
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
