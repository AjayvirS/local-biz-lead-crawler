from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
import tldextract

SOCIAL_OR_JUNK_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "maps.google.com",
    "goo.gl",
    "bit.ly",
}

FILE_EXT_BLACKLIST = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".zip", ".rar")


@dataclass(frozen=True)
class DirectoryConfig:
    name: str
    start_urls: list[str]
    pagination_selector: Optional[str] = None  # e.g. "a[rel='next']"
    include_text_hints: Optional[list[str]] = None  # e.g. ["Website", "Homepage"]
    max_pages: int = 50
    delay_seconds: float = 0.8


def _registrable_domain(url: str) -> str:
    ext = tldextract.extract(url)
    if not ext.domain:
        return ""
    return ".".join(p for p in [ext.domain, ext.suffix] if p)


def _is_http_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in ("http", "https")
    except Exception:
        return False


def _looks_like_business_site(url: str, directory_domain: str) -> bool:
    if not _is_http_url(url):
        return False

    u = url.lower()
    if any(u.endswith(ext) for ext in FILE_EXT_BLACKLIST):
        return False

    # Skip same-directory internal links
    if _registrable_domain(u) == directory_domain:
        return False

    # Skip obvious junk/social
    rd = _registrable_domain(u)
    if rd in SOCIAL_OR_JUNK_DOMAINS:
        return False

    return True


def _extract_outgoing_links(html: str, base_url: str, directory_domain: str, include_text_hints: Optional[list[str]]) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href:
            continue

        abs_url = urljoin(base_url, href)

        # Optional “text hints”: keep only anchors that look like website links on listings
        if include_text_hints:
            anchor_text = " ".join(a.get_text(" ", strip=True).split()).lower()
            if anchor_text:
                if not any(h.lower() in anchor_text for h in include_text_hints):
                    # If hints are provided, still allow if link itself looks like an external homepage
                    pass

        if _looks_like_business_site(abs_url, directory_domain):
            links.add(abs_url)

    return links


def _extract_next_page(html: str, base_url: str, selector: Optional[str]) -> Optional[str]:
    if not selector:
        return None
    soup = BeautifulSoup(html, "html.parser")
    a = soup.select_one(selector)
    if not a:
        return None
    href = a.get("href", "").strip()
    if not href:
        return None
    return urljoin(base_url, href)


async def crawl_directory(cfg: DirectoryConfig) -> list[tuple[str, str]]:
    """
    Returns [(business_url, discovered_from_url), ...]
    """
    results: list[tuple[str, str]] = []
    seen_pages: set[str] = set()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        headers={"User-Agent": "local-biz-lead-crawler/0.1 (+https://github.com/AjayvirS/local-biz-lead-crawler)"},
    ) as client:
        queue: list[str] = list(cfg.start_urls)
        directory_domain = _registrable_domain(cfg.start_urls[0])

        while queue and len(seen_pages) < cfg.max_pages:
            url = queue.pop(0)
            if url in seen_pages:
                continue
            seen_pages.add(url)

            try:
                r = await client.get(url)
                html = r.text
            except Exception:
                await asyncio.sleep(cfg.delay_seconds)
                continue

            outgoing = _extract_outgoing_links(html, url, directory_domain, cfg.include_text_hints)
            results.extend((u, url) for u in outgoing)

            next_url = _extract_next_page(html, url, cfg.pagination_selector)
            if next_url and next_url not in seen_pages:
                queue.append(next_url)

            await asyncio.sleep(cfg.delay_seconds)

    return results
