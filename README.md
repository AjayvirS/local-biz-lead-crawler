# local-biz-lead-crawler

A crawler that discovers local small-business websites, collects *non-invasive* quality signals (mobile readiness, basic SEO/accessibility hints, tech-stack fingerprints, etc.), and generates a ranked lead list you can browse in a simple UI. :contentReference[oaicite:1]{index=1}

> Goal: quickly build a “who should I contact?” list for local website improvement offers (freelance/agency outreach).

---

## What it does

This project is a small pipeline:

1) **Discover** business websites from directory/listing pages (e.g., Herold category pages)
2) **Analyze** each discovered site (HTTP status, title, basic checks, stack hints, score + reasons)
3) Store results in **SQLite** (`src/data/leads.sqlite`)
4) Browse and filter leads in a **Streamlit UI**, with per-lead detail pages

---

## Outputs

The SQLite database is the main artifact:

- `discovered_urls`  
  `url`, `discovered_from`, `discovered_at`

- `crawl_log`  
  `url`, `status_code`, `final_url`, `error`, `fetched_at`

- `site_analysis` (created by analysis step)  
  `url`, `final_url`, `status_code`, `title`, `https`, `has_viewport_meta`,
  contact presence flags (email/phone/address via regex),
  `stack_hint`, `score`, `reasons_json`

> Optional later: `llm_insights` for owner-friendly bullets & outreach text (only if you add it).

---

## Repo layout

- `src/configs/` – seed configuration (directory start URLs, pagination selector, etc.)
- `src/crawler/` – discovery + analysis pipeline code
- `src/scripts/` – helper scripts (reports/export)
- `src/ui/` – Streamlit analytics UI

---

## Setup

### Prerequisites

- Python 3.11+ recommended (3.12/3.13 usually fine too)
- A virtualenv tool (built-in `venv` is fine)

### Install

From repo root:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install -e .
```

### Configure Seeds

Enter the directory listing websites in `src/configs/seeds.yaml`

Example Structure:
```
directories:
  - name: "Herold"
    start_urls:
      - "https://www.herold.at/gelbe-seiten/wien/elektriker/"
    pagination:
      type: "next_link"
      selector: "a[rel='next']"
    max_pages: 30
    delay_seconds: 1.0
```
If your directory requires listing -> detail -> external website, configure that mode and selectors accordingly (your crawler supports this pattern).


### Run & Analyze

#### 1. Run Discovery
`python -m crawler.run_discovery` to run the discovery of the URLs provided in `seeds.yaml`

This should populate:

`src/data/leads.sqlite` -> `table discovered_urls`

#### 2. Run Analysis
`python -m crawler.run_analyze` to run the analysis of the discovered websites

This should populate:

`src/data/leads.sqlite` -> `table site_analysis`

`crawl_log` gets updated with fetch attempts/errors

#### 3. View Analytics through UI
`streamlit run src/ui/app.py`
Then open the URL Streamlit prints (by default on `http://localhost:8501`). This UI allows you to view the analytics in a UI friendly manner
