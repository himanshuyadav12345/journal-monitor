import csv,json
from datetime import datetime,timezone
from pathlib import Path
from monitor.filters import keep_article
from monitor.normalize import article_key
from monitor.sources.crossref import fetch_crossref
from monitor.sources.rss import fetch_rss

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/journals.json"; SEEN=ROOT/"data/seen.json"
OUT_JSON=ROOT/"output/latest.json"; OUT_CSV=ROOT/"output/latest.csv"

def main():
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    journals=[j for j in config["journals"] if j.get("enabled",True)]
    all_articles=[]; stats={}
    for j in journals:
        found=[]
        for section in ("issue","advance"):
            u=((j.get("sources") or {}).get(section) or {}).get("feed_url")
            if u: found.extend(fetch_rss(j,u,"publisher:"+section))
        if not found: found=fetch_crossref(j)
        found=[a for a in found if keep_article(j,a)]
        all_articles.extend(found); stats[j["id"]]=len(found)
    unique={}
    for a in all_articles: unique.setdefault(article_key(a),a)
    seen=set()
    if SEEN.exists():
        try: seen=set(json.loads(SEEN.read_text(encoding="utf-8")))
        except Exception: pass
    new=[a for k,a in unique.items() if k not in seen]
    seen.update(article_key(a) for a in new)
    OUT_JSON.parent.mkdir(parents=True,exist_ok=True)
    OUT_JSON.write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"new_count":len(new),
        "articles":[a.to_dict() for a in new],"source_stats":stats},ensure_ascii=False,indent=2),encoding="utf-8")
    with OUT_CSV.open("w",newline="",encoding="utf-8") as f:
        fields=["journal","journal_id","title","url","doi","published","updated","item_type","source","issue"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for a in new: w.writerow(a.to_dict())
    SEEN.parent.mkdir(parents=True,exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen),ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Journals checked: {len(journals)}")
    print(f"Unique records found: {len(unique)}")
    print(f"New records: {len(new)}")

if __name__=="__main__": main()
