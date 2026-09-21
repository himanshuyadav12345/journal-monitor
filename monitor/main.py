import csv,json
from datetime import datetime,timezone
from pathlib import Path
from monitor.filters import keep_article
from monitor.normalize import article_key
from monitor.sources.crossref import fetch_crossref
from monitor.sources.rss import fetch_rss
from monitor.sources.discovery import discover_feeds

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/journals.json"; SEEN=ROOT/"data/seen.json"
OUT_JSON=ROOT/"output/latest.json"; OUT_CSV=ROOT/"output/latest.csv"

def source_urls(journal):
    configured=journal.get("sources") or {}
    discovered=discover_feeds(journal)
    urls={}
    for section in ("issue","advance"):
        configured_url=((configured.get(section) or {}).get("feed_url"))
        urls[section]=configured_url or discovered.get(section)
    return urls

def main():
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    journals=[j for j in config["journals"] if j.get("enabled",True)]
    all_articles=[]; stats={}; source_stats={}
    for j in journals:
        found=[]
        urls=source_urls(j)
        for section in ("issue","advance"):
            u=urls.get(section)
            if u:
                found.extend(fetch_rss(j,u,"publisher:"+section))
        if not found:
            found=fetch_crossref(j)
        found=[a for a in found if keep_article(j,a)]
        all_articles.extend(found)
        stats[j["id"]]=len(found)
        source_stats[j["id"]]={"issue":bool(urls.get("issue")),"advance":bool(urls.get("advance")),"records":len(found)}
    unique={}
    for a in all_articles: unique.setdefault(article_key(a),a)
    seen=set()
    if SEEN.exists():
        try: seen=set(json.loads(SEEN.read_text(encoding="utf-8")))
        except Exception: pass
    new=[a for k,a in unique.items() if k not in seen]
    seen.update(article_key(a) for a in new)
    OUT_JSON.parent.mkdir(parents=True,exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "new_count":len(new),
        "candidate_count":len(unique),
        "articles":[a.to_dict() for a in new],
        "source_stats":stats,
        "source_availability":source_stats
    },ensure_ascii=False,indent=2),encoding="utf-8")
    with OUT_CSV.open("w",newline="",encoding="utf-8") as f:
        fields=["journal","journal_id","title","url","doi","published","updated","item_type","source","issue"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for a in new: w.writerow(a.to_dict())
    SEEN.parent.mkdir(parents=True,exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen),ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Journals checked: {len(journals)}")
    print(f"Unique candidate records found: {len(unique)}")
    print(f"New records: {len(new)}")
    publisher_count=sum(1 for x in source_stats.values() if x["issue"] or x["advance"])
    print(f"Journals with publisher source available: {publisher_count}")

if __name__=="__main__": main()
