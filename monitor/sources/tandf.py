import re
import requests
from monitor.normalize import normalize_doi

HEADERS={"User-Agent":"journal-monitor/1.2 (academic metadata monitor)"}

def latest_article_dois(journal):
    homepage=journal.get("homepage") or ""
    m=re.search(r"/journals/([^/?#]+)",homepage)
    if not m: return set()
    url=f"https://www.tandfonline.com/action/showAxaArticles?journalCode={m.group(1)}"
    try:
        r=requests.get(url,headers=HEADERS,timeout=30)
        r.raise_for_status()
    except Exception:
        return set()
    dois=set()
    for href in re.findall(r'href=["\']([^"\']*?/doi/(?:abs|full|pdf)/[^"\']+)["\']',r.text,re.I):
        mdoi=re.search(r'/doi/(?:abs|full|pdf)/(10\.\d{4,9}/[^?#"\'&<>]+)',href,re.I)
        if mdoi:
            dois.add(normalize_doi(mdoi.group(1)))
    return {d for d in dois if d}

def filter_tandf_advance(journal,crossref_articles):
    dois=latest_article_dois(journal)
    if not dois: return []
    out=[]
    for a in crossref_articles:
        if normalize_doi(a.doi or "") in dois:
            a.source="publisher:advance"
            a.stage="online_first"
            a.issue=None
            out.append(a)
    return out
