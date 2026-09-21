from monitor.normalize import normalize_text

FRONT_MATTER_TERMS=("cover","front matter","back matter","contents","table of contents","editorial board","masthead","contributors")

def keep_article(journal, article):
    f=journal.get("filters",{}) or {}
    title=normalize_text(article.title)
    if f.get("exclude_front_back_matter") and any(x in title for x in FRONT_MATTER_TERMS):
        return False
    keep_types=f.get("default_keep_article_types") or f.get("default_keep")
    if keep_types:
        raw=normalize_text(article.item_type or "")
        normalized=raw.replace("_"," ").replace("-"," ")
        allowed={normalize_text(x).replace("_"," ").replace("-"," ") for x in keep_types}
        if normalized and normalized not in allowed:
            return False
    return True
