import csv,json
from datetime import datetime,timezone
from pathlib import Path
from monitor.filters import keep_article
from monitor.normalize import article_key
from monitor.sources.crossref import fetch_crossref, classify_tandf_crossref
from monitor.sources.rss import fetch_rss
from monitor.sources.discovery import discover_feeds
from monitor.quality import keep_fresh

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
    all_articles=[]; stats={}; source_stats={}; rejected_stale={}
    for j in journals:
        urls=source_urls(j)
        publisher=(j.get("publisher") or "").lower()
        if "taylor & francis" in publisher:
            crossref_articles=fetch_crossref(j,max_age_days=180)
            issue_articles,advance_articles=classify_tandf_crossref(j,crossref_articles)
            found=issue_articles+advance_articles
            source_stats[j["id"]]={
                "issue":False,"advance":False,"fallback":"crossref",
                "records":0,"raw_records":len(crossref_articles),"stale_rejected":0,
                "tandf_rss_records":0,
                "tandf_issue_records":len(issue_articles),
                "tandf_online_first_records":len(advance_articles),
                "crossref_records":len(crossref_articles)
            }
        else:
            found=[]
            for section in ("issue","advance"):
                u=urls.get(section)
                if u: found.extend(fetch_rss(j,u,"publisher:"+section))
            if not found: found=fetch_crossref(j)
            source_stats[j["id"]]={
                "issue":bool(urls.get("issue")),"advance":bool(urls.get("advance")),
                "records":0,"raw_records":len(found),"stale_rejected":0
            }
        before=len(found)
        found=[a for a in found if keep_article(j,a)]
        after_filters=len(found)
        found=[a for a in found if keep_fresh(j,a)]
        rejected_stale[j["id"]]=after_filters-len(found)
        source_stats[j["id"]]["records"]=len(found)
        source_stats[j["id"]]["stale_rejected"]=rejected_stale[j["id"]]
        all_articles.extend(found)
        stats[j["id"]]=len(found)
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
        "new_count":len(new),"candidate_count":len(unique),
        "articles":[a.to_dict() for a in new],
        "source_stats":stats,"source_availability":source_stats,
        "quality_control":{"publisher_max_age_days":540,"stale_records_rejected":sum(rejected_stale.values())}
    },ensure_ascii=False,indent=2),encoding="utf-8")
    with OUT_CSV.open("w",newline="",encoding="utf-8") as f:
        fields=["journal","journal_id","title","url","doi","published","updated","item_type","source","issue","stage"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for a in new: w.writerow(a.to_dict())
    SEEN.parent.mkdir(parents=True,exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen),ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Journals checked: {len(journals)}")
    print(f"Unique candidate records found: {len(unique)}")
    print(f"New records: {len(new)}")
    print(f"Stale publisher records rejected: {sum(rejected_stale.values())}")
    publisher_count=sum(1 for x in source_stats.values() if x["issue"] or x["advance"])
    print(f"Journals with publisher source available: {publisher_count}")

if __name__=="__main__": main()
