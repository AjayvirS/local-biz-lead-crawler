from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from crawler.store import Store
from crawler.analyze import (
    extract_title,
    has_viewport_meta,
    extract_contact_presence,
    detect_stack_hint,
    is_https,
)
from crawler.score import score_site


async def analyze_site(client: httpx.AsyncClient, store: Store, url: str) -> None:
    try:
        r = await client.get(url, follow_redirects=True)
        status = r.status_code
        final_url = str(r.url)
        html = r.text
        if "text/html" not in ct and "application/xhtml" not in ct:
            ct = (r.headers.get("content-type") or "").lower()
            store.log_fetch(url, r.status_code, str(r.url), f"non_html:{ct}")

    except Exception as e:
        store.log_fetch(url, None, None, f"fetch_failed:{type(e).__name__}:{e}")
        return

    title = extract_title(html)
    viewport = has_viewport_meta(html)
    has_email, has_phone, has_address = extract_contact_presence(html)
    stack_hint = detect_stack_hint(html)
    https_flag = is_https(final_url)

    score, reasons = score_site(
        https=https_flag,
        has_viewport=viewport,
        title=title,
        has_email=has_email,
        has_phone=has_phone,
        has_address=has_address,
        stack_hint=stack_hint,
    )

    store.upsert_site_analysis(
        url=url,
        final_url=final_url,
        status_code=status,
        https=https_flag,
        title=title,
        has_viewport=viewport,
        has_email=has_email,
        has_phone=has_phone,
        has_address=has_address,
        stack_hint=stack_hint,
        score=score,
        reasons=reasons,
    )


async def main(limit: int = 500) -> None:
    root = Path(__file__).resolve().parents[2]
    db_path = root / "src" / "data" / "leads.sqlite"

    store = Store(str(db_path))
    urls = store.get_discovered_urls(limit=limit)

    if not urls:
        raise RuntimeError("No discovered URLs found. Run discovery first.")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        headers={"User-Agent": "local-biz-lead-crawler/0.1"},
    ) as client:
        for i, url in enumerate(urls, 1):
            await analyze_site(client, store, url)

            if i % 25 == 0:
                print(f"Analyzed {i}/{len(urls)}")

    print("Analysis complete.")


if __name__ == "__main__":
    asyncio.run(main())