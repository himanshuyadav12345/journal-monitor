import re
from urllib.parse import urljoin
import requests

HEADERS={"User-Agent":"journal-monitor/1.2 (academic metadata monitor)"}

def _links(html, base_url):
    out=[]
    for m in re.finditer(r'<(?:a|link)\b[^>]*?(?:href=["\']([^"\']+)["\'])[^>]*>', html, re.I):
        tag=m.group(0)
        href=urljoin(base_url,m.group(1))
        text=re.sub(r"<[^>]+>"," ",tag)
        out.append((href, text.lower()))
    return out

def _homepage_html(url):
    if not url:
        return ""
    try:
        r=requests.get(url,headers=HEADERS,timeout=25)
        r.raise_for_status()
        return r.text
    except Exception:
        return ""

def _find_feed_links(url):
    html=_homepage_html(url)
    links=_links(html,url)
    feeds=[]
    for href,text in links:
        blob=(href+" "+text).lower()
        if any(x in blob for x in ("rss","feed","atom","xml")):
            feeds.append((href,blob))
    return feeds

def discover_feeds(journal):
    publisher=(journal.get("publisher") or "").lower()
    homepage=journal.get("homepage") or ""

    if "new left review" in publisher or "newleftreview.org" in homepage:
        return {"issue":"https://newleftreview.org/feed","advance":"https://newleftreview.org/feed"}

    if "taylor & francis" in publisher:
        m=re.search(r"/journals/([^/?#]+)",homepage)
        if m:
            feed=f"https://www.tandfonline.com/feed/rss/{m.group(1)}"
            return {"issue":feed,"advance":feed}

    if "sage" in publisher:
        m=re.search(r"/home/([^/?#]+)",homepage,re.I)
        if m:
            code=m.group(1)
            connected=urljoin(homepage,f"../../connected/{code}")
            feeds=_find_feed_links(connected)
            issue=None
            advance=None
            generic=None
            for href,blob in feeds:
                if any(x in blob for x in ("onlinefirst","online-first","axatoc")):
                    advance=advance or href
                elif any(x in blob for x in ("etoc","table of contents","recent articles","latest articles")):
                    issue=issue or href
                else:
                    generic=generic or href
            return {"issue":issue or generic,"advance":advance or generic}

    # Oxford and Cambridge expose RSS links in the page head or journal pages.
    feeds=_find_feed_links(homepage)
    issue=None
    advance=None
    generic=None
    for href,blob in feeds:
        if any(x in blob for x in ("advance","onlinefirst","firstview","first-view")):
            advance=advance or href
        elif any(x in blob for x in ("latest issue","current issue","table of contents","toc","latest-issue")):
            issue=issue or href
        else:
            generic=generic or href

    if "oxford academic" in publisher:
        # The advance-articles page is separate from the journal homepage.
        advance_url=urljoin(homepage,"advance-articles")
        for href,blob in _find_feed_links(advance_url):
            advance=advance or href
        # If the homepage did not expose a current-issue feed, inspect latest issue.
        if not issue:
            latest_url=urljoin(homepage,"latest-issue")
            for href,blob in _find_feed_links(latest_url):
                issue=issue or href

    return {"issue":issue or generic,"advance":advance or generic}
