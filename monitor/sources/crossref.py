import requests
from dateutil import parser as dateparser
from monitor.models import Article

API="https://api.crossref.org/journals/{issn}/works"
HEADERS={"User-Agent":"journal-monitor/1.0 (academic metadata monitor)"}

def fetch_crossref(journal, rows=50):
    issn=journal.get("issn",{}).get("online") or journal.get("issn",{}).get("print")
    if not issn: return []
    try:
        r=requests.get(API.format(issn=issn),params={"rows":rows,"sort":"published","order":"desc",
            "select":"DOI,title,URL,published,issued,created,type,issue,container-title"},headers=HEADERS,timeout=30)
        r.raise_for_status()
        items=r.json().get("message",{}).get("items",[])
    except Exception: return []
    out=[]
    for x in items:
        title=(x.get("title") or [""])[0].strip()
        if not title: continue
        def d(key):
            vals=(x.get(key) or {}).get("date-parts")
            if vals and vals[0]:
                try: return dateparser.parse("-".join(str(v) for v in vals[0])).isoformat()
                except Exception: pass
            return None
        out.append(Article(journal=journal["name"],journal_id=journal["id"],title=title,url=x.get("URL") or "",
            doi=x.get("DOI"),published=d("published") or d("issued") or d("created"),
            updated=d("created"),item_type=x.get("type"),source="crossref",issue=x.get("issue")))
    return out
