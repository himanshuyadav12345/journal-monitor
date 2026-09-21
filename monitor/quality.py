from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser

# Publisher feeds can expose long historical backlogs. This is deliberately
# generous enough to cover slow/annual journals without turning an archive
# feed into a stream of "new" records.
DEFAULT_PUBLISHER_MAX_AGE_DAYS = 540


def article_date(article):
    for value in (article.published, article.updated):
        if value:
            try:
                return dateparser.parse(value).astimezone(timezone.utc)
            except Exception:
                pass
    return None


def freshness_limit(journal, source):
    configured = (journal.get("monitoring") or {}).get("max_publisher_age_days")
    if source.startswith("publisher:"):
        return int(configured or DEFAULT_PUBLISHER_MAX_AGE_DAYS)
    return None


def keep_fresh(journal, article):
    limit = freshness_limit(journal, article.source or "")
    if limit is None:
        return True
    published = article_date(article)
    # Missing dates should not silently make us declare a journal inactive or
    # lose a legitimate current issue. Let the publisher source stand.
    if published is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=limit)
    return published >= cutoff
