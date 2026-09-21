from monitor.normalize import normalize_text
FRONT_MATTER_TERMS=("cover","front matter","back matter","contents","table of contents","editorial board","masthead","contributors")

def keep_article(journal, article):
    f=journal.get("filters",{}) or {}
    title=normalize_text(article.title)
    if f.get("exclude_front_back_matter") and any(x in title for x in FRONT_MATTER_TERMS):
        return False
    return True
