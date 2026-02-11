from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from crawler.discover.directory import DirectoryConfig, crawl_directory
from crawler.store import Store


def _repo_root() -> Path:
    # .../local-biz-lead-crawler/src/crawler/run_discovery.py
    # parents[0] = crawler
    # parents[1] = src
    # parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def load_configs(path: str | Path) -> list[DirectoryConfig]:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    cfgs: list[DirectoryConfig] = []
    for d in data.get("directories", []):
        pagination = d.get("pagination", {}) or {}
        rules = d.get("rules", {}) or {}

        cfgs.append(
            DirectoryConfig(
                name=d["name"],
                start_urls=d["start_urls"],
                pagination_selector=pagination.get("selector"),
                include_text_hints=rules.get("include_text_hints"),
                max_pages=int(d.get("max_pages", 50)),
                delay_seconds=float(d.get("delay_seconds", 0.8)),
                mode=d.get("mode", "external_from_listing"),
                detail_link_selector=d.get("detail_link_selector"),
                external_link_selectors=d.get("external_link_selectors"),
                max_detail_pages_per_listing=int(d.get("max_detail_pages_per_listing", 30)),
            )
        )
    return cfgs


async def main() -> None:
    root = _repo_root()
    config_path = root / "src" / "configs" / "seeds.yaml"
    db_path = root / "src" / "data" / "leads.sqlite"

    store = Store(str(db_path))
    cfgs = load_configs(config_path)

    for cfg in cfgs:
        pairs = await crawl_directory(cfg)
        # pairs are (business_url, discovered_from_url)
        store.bulk_upsert_discovered(pairs)

    print(f"Done. Stored discoveries in {db_path}")


if __name__ == "__main__":
    asyncio.run(main())