import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

def normalize_text(value):
    value = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"\s+", " ", value).strip()

def canonical_url(url):
    if not url: return ""
    p = urlsplit(url.strip())
    query = re.sub(r"(^|&)(utm_[^=]+|fbclid|gclid)=[^&]*", "", p.query, flags=re.I)
    query = re.sub(r"&&+", "&", query).strip("&")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), query, ""))

def normalize_doi(doi):
    if not doi: return ""
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return doi.lower().strip()

def article_key(article):
    doi = normalize_doi(article.doi or "")
    if doi: return "doi:" + doi
    url = canonical_url(article.url or "")
    if url: return "url:" + url
    date = (article.published or article.updated or "")[:10]
    return "title:" + normalize_text(article.title) + "|" + date
