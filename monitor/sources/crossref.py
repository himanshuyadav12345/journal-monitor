import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from monitor.models import Article
from monitor.normalize import normalize_doi

API="https://api.crossref.org/journals/{issn}/works"
HEADERS={"User-Agent":"journal-monitor/1.1 (academic metadata monitor)"}

def _crossref_items(journal, rows=100, max_age_days=90):
    issn=journal.get("issn",{}).get("online") or journal.get("issn",{}).get("print")
    if not issn: return []
    cutoff=(datetime.now(timezone.utc)-timedelta(days=max_age_days)).date().isoformat()
    try:
        r=requests.get(API.format(issn=issn),params={
            "rows":rows,"sort":"published","order":"desc",
            "filter":f"from-pub-date:{cutoff}",
            "select":"DOI,title,URL,published,issued,created,type,issue,container-title"
        },headers=HEADERS,timeout=30)
        r.raise_for_status()
        return r.json().get("message",{}).get("items",[])
    except Exception:
        return []

def _date(x,key):
    vals=(x.get(key) or {}).get("date-parts")
    if vals and vals[0]:
        try: return dateparser.parse("-".join(str(v) for v in vals[0])).isoformat()
        except Exception: pass
    return None

def _article(journal,x,source):
    title=(x.get("title") or [""])[0].strip()
    if not title: return None
    return Article(
        journal=journal["name"],journal_id=journal["id"],title=title,url=x.get("URL") or "",
        doi=normalize_doi(x.get("DOI") or "") or None,
        published=_date(x,"published") or _date(x,"issued") or _date(x,"created"),
        updated=_date(x,"created"),item_type=x.get("type"),source=source,
        issue=x.get("issue")
    )

def fetch_crossref(journal, rows=100, max_age_days=90):
    out=[]
    for x in _crossref_items(journal,rows,max_age_days):
        a=_article(journal,x,"crossref_recent")
        if a: out.append(a)
    return out

def classify_tandf_issue(journal, rss_articles):
    """
    T&F's publication RSS is a recent-article feed, not an issue-only feed.
    Crossref issue metadata is therefore used to retain only articles already
    assigned to an issue. This is classification, not a replacement source.
    """
    items=_crossref_items(journal)
    by_doi={normalize_doi(x.get("DOI") or ""):x for x in items if x.get("DOI")}
    out=[]
    for a in rss_articles:
        x=by_doi.get(normalize_doi(a.doi or ""))
        if x and x.get("issue"):
            a.issue=x.get("issue")
            a.stage="issue"
            out.append(a)
    return out
