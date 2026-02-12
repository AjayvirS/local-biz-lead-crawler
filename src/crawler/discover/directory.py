from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import tldextract
from bs4 import BeautifulSoup

# Registrable junk domains to skip as non-business targets.
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

# Extra string-based filters
SOCIAL_OR_JUNK_SUBSTRINGS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "maps.google.",
    "goo.gl",
    "bit.ly",
    "wa.me",
    "whatsapp.com",
    "tel:",
    "mailto:",
)

FILE_EXT_BLACKLIST = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".zip", ".rar")


@dataclass(frozen=True)
class DirectoryConfig:
    name: str
    start_urls: list[str]

    # Listing pagination
    pagination_selector: Optional[str] = None 
    max_pages: int = 50
    delay_seconds: float = 0.8


    include_text_hints: Optional[list[str]] = None

    mode: str = "external_from_listing"  # or "detail_then_external"
    detail_link_selector: str | None = None
    external_link_selectors: list[str] | None = None

    # Optional: cap detail pages per listing page (politeness + speed)
    max_detail_pages_per_listing: int = 30


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


def _is_junk_url(url: str) -> bool:
    u = url.lower()
    if any(u.endswith(ext) for ext in FILE_EXT_BLACKLIST):
        return True
    if any(s in u for s in SOCIAL_OR_JUNK_SUBSTRINGS):
        return True
    rd = _registrable_domain(u)
    if rd in SOCIAL_OR_JUNK_DOMAINS:
        return True
    return False


def _looks_like_business_site(url: str, directory_domain: str) -> bool:
    # Only accept external http(s) pages
    if not _is_http_url(url):
        return False

    # Skip same-directory internal links
    if _registrable_domain(url) == directory_domain:
        return False

    # Skip obvious junk/social
    if _is_junk_url(url):
        return False

    return True


def _extract_outgoing_links(
    html: str,
    base_url: str,
    directory_domain: str,
    include_text_hints: Optional[list[str]],
) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue

        abs_url = urljoin(base_url, href)

        # IMPORTANT: This is a soft filter; we only skip when hints exist and anchor text clearly doesn't match.
        if include_text_hints:
            anchor_text = " ".join(a.get_text(" ", strip=True).split()).lower()
            if anchor_text and not any(h.lower() in anchor_text for h in include_text_hints):
                # Soft skip only if it doesn't look like an external homepage anyway
                # (e.g., some directories use icons, no text)
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
    href = (a.get("href") or "").strip()
    if not href:
        return None
    return urljoin(base_url, href)


def _select_links(html: str, base_url: str, selector: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    out: set[str] = set()
    for a in soup.select(selector):
        href = (a.get("href") or "").strip()
        if href:
            out.add(urljoin(base_url, href))
    return out


def _extract_external_from_detail(
    html: str,
    base_url: str,
    directory_domain: str,
    selectors: list[str] | None,
) -> set[str]:
    """
    Extract external business URLs from a detail page.
    For Herold, a good selector is: a[target='_blank'][href^='http']
    """
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()

    if selectors:
        candidates = []
        for sel in selectors:
            candidates.extend(soup.select(sel))
    else:
        candidates = soup.select("a[href]")

    for a in candidates:
        href = (a.get("href") or "").strip()
        if not href:
            continue

        abs_url = urljoin(base_url, href)

        # Must be external business site (not herold, not social, not junk)
        if _looks_like_business_site(abs_url, directory_domain):
            links.add(abs_url)

    return links


async def crawl_directory(cfg: DirectoryConfig) -> list[tuple[str, str]]:
    """
    Returns [(business_url, discovered_from_url), ...]
    discovered_from_url is:
      - listing page URL in mode=external_from_listing
      - detail page URL in mode=detail_then_external
    """
    results: list[tuple[str, str]] = []
    seen_pages: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()  # (business_url, discovered_from)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        headers={
            "User-Agent": "local-biz-lead-crawler/0.1 (+https://github.com/AjayvirS/local-biz-lead-crawler)"
        },
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

            print(f"[{cfg.name}] Listing page: {url}")
            # MODE 1: listing already contains external business sites
            if cfg.mode == "external_from_listing":
                outgoing = _extract_outgoing_links(
                    html=html,
                    base_url=url,
                    directory_domain=directory_domain,
                    include_text_hints=cfg.include_text_hints,
                )
                for u in outgoing:
                    pair = (u, url)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        results.append(pair)

            elif cfg.mode == "detail_then_external":
                if not cfg.detail_link_selector:
                    raise ValueError(
                        f"{cfg.name}: mode=detail_then_external requires detail_link_selector"
                    )

                detail_urls = _select_links(html, url, cfg.detail_link_selector)

                detail_urls = {d for d in detail_urls if _registrable_domain(d) == directory_domain}

                for durl in list(detail_urls)[: cfg.max_detail_pages_per_listing]:
                    print(f"  → detail: {durl}")
                    try:
                        dr = await client.get(durl)
                        dhtml = dr.text
                    except Exception:
                        await asyncio.sleep(cfg.delay_seconds)
                        continue

                    external_links = _extract_external_from_detail(
                        html=dhtml,
                        base_url=durl,
                        directory_domain=directory_domain,
                        selectors=cfg.external_link_selectors,
                    )

                    for ext in external_links:
                        pair = (ext, durl)
                        if pair not in seen_pairs:
                            seen_pairs.add(pair)
                            results.append(pair)

                    await asyncio.sleep(cfg.delay_seconds)

            else:
                raise ValueError(f"Unknown cfg.mode: {cfg.mode}")

            next_url = _extract_next_page(html, url, cfg.pagination_selector)
            if next_url and next_url not in seen_pages:
                queue.append(next_url)

            await asyncio.sleep(cfg.delay_seconds)

    return results
