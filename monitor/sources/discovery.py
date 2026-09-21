import re
from urllib.parse import urljoin
import requests

HEADERS={"User-Agent":"journal-monitor/1.1 (academic metadata monitor)"}

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
            base="https://journals.sagepub.com/action/showFeed"
            return {
                "issue":f"{base}?type=etoc&feed=rss&jc={code}",
                "advance":f"{base}?type=axatoc&feed=rss&jc={code}"
            }
    html=_homepage_html(homepage)
    links=_links(html,homepage)
    issue=None
    advance=None
    generic=None
    for href,text in links:
        blob=(href+" "+text).lower()
        if not any(x in blob for x in ("rss","feed","atom","xml")):
            continue
        if any(x in blob for x in ("advance","onlinefirst","firstview","first-view")):
            advance=advance or href
        elif any(x in blob for x in ("latest issue","current issue","table of contents","toc")):
            issue=issue or href
        else:
            generic=generic or href
    if "oxford academic" in publisher and not advance:
        advance_url=urljoin(homepage,"advance-articles")
        ah=_homepage_html(advance_url)
        for href,text in _links(ah,advance_url):
            blob=(href+" "+text).lower()
            if "rss" in blob or "feed" in blob:
                advance=href
                break
    return {"issue":issue or generic,"advance":advance or generic}
