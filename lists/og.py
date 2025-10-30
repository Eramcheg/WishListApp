import time
from urllib.parse import urljoin, urlparse

import cloudscraper
import requests
from bs4 import BeautifulSoup

from lists.audit import log_event


def enrich_from_url(url: str):
    """
    Возвращает {"title": ..., "image_url": ...} на основе OpenGraph мета-тегов.
    """
    if not url:
        return {}
    start = time.time()
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    sess = requests.Session()
    parsed = urlparse(url)
    host = parsed.netloc or "unknown"
    origin = f"{parsed.scheme}://{parsed.netloc}"

    try:
        sess.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; "
                "Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": origin,
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

        resp = scraper.get(url, timeout=10)
        elapsed = int((time.time() - start) * 1000)

        if resp.status_code in (401, 403, 429, 503):
            log_event(
                "og.fetch.denied",
                None,
                None,
                host=host,
                status=resp.status_code,
                ms=elapsed,
                reason="blocked",
            )
            return {}

        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        def _meta(prop=None, name=None):
            if prop:
                tag = soup.find("meta", property=prop)
            else:
                tag = soup.find("meta", attrs={"name": name})
            return (tag.get("content") or "").strip() if tag and tag.get("content") else ""

        title = (
            _meta(prop="og:title")
            or _meta(name="twitter:title")
            or (soup.title.string.strip() if soup.title and soup.title.string else "")
        )

        image = _meta(prop="og:image") or _meta(name="twitter:image")
        if image:
            image = urljoin(url, image)

        data = {}
        if title:
            data["title"] = title
        if image:
            data["image_url"] = image

        log_event(
            "og.fetch.ok",
            None,
            None,
            host=host,
            ms=elapsed,
            has_title=bool(title),
            has_image=bool(image),
        )
        return data

    except requests.Timeout:
        elapsed = int((time.time() - start) * 1000)
        log_event("og.fetch.timeout", None, None, host=host, ms=elapsed)
        return {}
    except requests.RequestException as e:
        elapsed = int((time.time() - start) * 1000)
        log_event("og.fetch.error", None, None, host=host, err=str(e)[:100], ms=elapsed)
        return {}
