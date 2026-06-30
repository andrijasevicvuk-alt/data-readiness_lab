# data-readiness_lab

This repository is a YPI side repo for source-readiness research, parser prototyping, and early dataset-quality checks.

It is not the main YPI application and it is not a production scraping repo. Successful source adapters, dataset-pilot logic, and duplicate-verification logic will later be moved into the main YPI repo once they are stable enough to promote.

This repository is a small research harness for checking whether public boating-related websites are technically suitable as data sources for YPI research.

The goal is not to scrape large amounts of data. The goal is to make a few slow, polite requests to public pages and record whether a source appears technically usable, blocked, or unsuitable.

## Rules

- Use a clear research user agent.
- Keep requests slow and polite.
- Only probe a few public pages per source.
- Check `robots.txt` and `sitemap.xml` where available.
- If a source returns HTTP `403`, record it as `blocked_403_do_not_bypass`.
- Do not attempt bypass techniques.
- Do not access private, authenticated, or hidden content.

## Sources In Scope

- Boat24
- Boat24 archives if public/archive pages exist
- Marine One
- Croatian Yachting
- iNautia
- Yachtall
- TheYachtMarket
- TopBoats
- Band of Boats
- Njuskalo Nautika
- Burza Nautike
- boats.com
- Boatshop24
- Botentekoop
- Apollo Duck
- Boatshed
- YachtWorld

## Project Layout

- `src/ypi_source_lab/`: shared Python framework code
- `sources/<source_name>/probe.py`: source-specific probe logic
- `sources/<source_name>/notes.md`: source notes and assumptions
- `docs/source_decision_matrix.md`: classification rules
- `results/`: JSON and CSV outputs

## Setup

Python 3.11+ is recommended.

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

This project currently uses only Python standard library modules, so there are no third-party dependencies.

## Run

Run all source probes:

```powershell
python run_probes.py
```

Outputs:

- `results/source_tests.json`
- `results/source_tests.csv`
- `results/field_probe_results.json`
- `results/field_probe_results.csv`

Run the small rendered-text comparison probe:

```powershell
python run_rendered_text_probe.py
```

Additional outputs:

- `results/rendered_text_probe_results.json`
- `results/rendered_text_probe_results.csv`

Run the consolidated readiness report:

```powershell
python run_source_readiness_report.py
```

Additional outputs:

- `results/source_readiness_report.json`
- `results/source_readiness_report.csv`
- `docs/source_readiness_report.md`

## Dataset Pilot

The first controlled dataset pilot combines:

- `TheYachtMarket` as the broader marketplace backbone
- `Marine One / YachtBrokerage` as the local broker trust-anchor

Run the pilot:

```powershell
python run_dataset_pilot.py
```

Outputs:

- `results/market_dataset_pilot_raw.json`
- `results/market_dataset_pilot_raw.csv`
- `results/duplicate_candidates.json`
- `results/duplicate_candidates.csv`

This pilot exists to prove whether a small, controlled public-market sample can support YPI valuation usefulness first, and insurance-department support later.

Run the normalized preview:

```powershell
python run_normalized_preview.py
```

Additional outputs:

- `results/normalized_dataset_preview.json`
- `results/normalized_dataset_preview.csv`

Run the valuation-readiness report:

```powershell
python run_valuation_readiness_report.py
```

Additional outputs:

- `results/valuation_readiness_report.json`
- `results/valuation_readiness_report.csv`
- `docs/valuation_readiness_report.md`

Run the bounded Wave 2 and delayed-source pass:

```powershell
python run_wave2_probes.py
```

Additional outputs:

- `results/wave2_source_tests.json`
- `results/wave2_source_tests.csv`
- `results/wave2_field_probe_results.json`
- `results/wave2_field_probe_results.csv`
- `docs/wave2_and_delayed_source_report.md`

## Current Best Pair

- `TheYachtMarket` is the current best broader marketplace backbone candidate.
- `Marine One / YachtBrokerage` is the current best local broker trust-anchor candidate.
- Together, this pair is the strongest current path toward a first YPI MVP dataset without relying on blocked `403` sources.

## Public Repo Scope

- This repo is intentionally limited to source-readiness checks, tiny parser prototypes, dataset-pilot outputs, and duplicate-review logic.
- It does not contain anti-bot bypass logic, proxy rotation, copied cookies, CAPTCHA handling, or large-scale scraping workflows.
- Sources that block automated access remain delayed or permission/feed/API candidates instead of bypass targets.
- When a source adapter or dataset workflow proves useful enough for the core product, the implementation should be promoted into the main YPI repo rather than expanded here indefinitely.

## From Source Lab To Main YPI Repo

- This repo proves source access, parser feasibility, dataset quality, and duplicate-review logic before promotion.
- `TheYachtMarket` and `Marine One / YachtBrokerage` are the current best pair for controlled transfer into later main-repo ingestion work.
- `results/market_dataset_pilot_raw.*` and `results/normalized_dataset_preview.*` are the clearest bridge outputs for future raw-ingestion and normalization layers.
- Successful source-specific parser modules should later move into the main YPI repo as real adapters, while blocked or rendering-dependent sources should remain research-only here.

## Localized Marine Text Extraction Idea

This repo may later stage unparsed localized marine text and reviewed regex or rule candidates.
This is only a review-assisted rule discovery process.
Accepted deterministic rules may later transfer to the main YPI pipeline after fixture tests.

## Wave 2 Readout

- The latest bounded Wave 2 pass did not find a stronger new backbone source than `TheYachtMarket`.
- `boats.com`, `Boatshop24`, `Botentekoop`, `Boatshed`, and `YachtWorld` all returned public challenge or `403` behavior to the raw probe client and remain blocked in this lab.
- `Apollo Duck` was reachable, but its tested country paths behaved like generic fallback pages rather than clearly country-filtered result buckets, so it remains `not_ready`.
- Delayed-source near-term decisions are now:
  `Croatian Yachting` -> `rendered_adapter_candidate`
  `Burza Nautike` -> `delayed_detail_discovery`
  `Yachtall` -> `not_worth_pursuing_now`
  `Njuskalo Nautika` -> `blocked_do_not_bypass`

## Notes

- Some source domains are based on current public brand/domain assumptions and are documented in each source `notes.md`.
- A `403` result is treated as an explicit stop signal for this research harness.
- Rendered-text checks are allowed only for already-accessible public `200` pages and only to compare raw HTTP text versus visible public browser text.
- If a site is unavailable during a run, that does not automatically mean it is a bad source; it only means the probe could not verify suitability at that time.
