import asyncio
from pathlib import Path

import yaml  # pip install pyyaml

from crawler.discover.directory import DirectoryConfig, crawl_directory
from crawler.store import Store


def load_configs(path: str) -> list[DirectoryConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cfgs = []
    for d in data.get("directories", []):
        cfgs.append(
            DirectoryConfig(
                name=d["name"],
                start_urls=d["start_urls"],
                pagination_selector=d.get("pagination", {}).get("selector"),
                include_text_hints=d.get("rules", {}).get("include_text_hints"),
                max_pages=int(d.get("max_pages", 50)),
                delay_seconds=float(d.get("delay_seconds", 0.8)),
            )
        )
    return cfgs


async def main():
    store = Store("data/leads.sqlite")
    cfgs = load_configs("configs/seeds.yaml")

    for cfg in cfgs:
        pairs = await crawl_directory(cfg)
        store.bulk_upsert_discovered(pairs)

    print("Done. Discovered URLs stored in data/leads.sqlite")


if __name__ == "__main__":
    asyncio.run(main())
