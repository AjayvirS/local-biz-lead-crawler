from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s()./-]{6,}\d)")
ADDRESS_HINT_RE = re.compile(
    r"\b(straße|strasse|gasse|platz|weg|allee|\d{4}\s+[A-Za-zÄÖÜäöüß])\b",
    re.I,
)


def extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split()).strip()
    return None


def has_viewport_meta(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.select_one('meta[name="viewport"]')
    return bool(tag and tag.get("content"))


def extract_contact_presence(html: str) -> tuple[bool, bool, bool]:
    has_email = bool(EMAIL_RE.search(html))
    has_phone = bool(PHONE_RE.search(html))
    has_address = bool(ADDRESS_HINT_RE.search(html))
    return has_email, has_phone, has_address


def detect_stack_hint(html: str) -> str | None:
    h = html.lower()

    if "wp-content" in h or "wp-includes" in h or "wordpress" in h:
        return "wordpress"

    if "joomla" in h:
        return "joomla"

    if "wix.com" in h or "wixsite" in h:
        return "wix"

    if "squarespace" in h:
        return "squarespace"

    if "webflow" in h:
        return "webflow"

    return None


def is_https(url: str) -> bool:
    try:
        return urlparse(url).scheme == "https"
    except Exception:
        return False