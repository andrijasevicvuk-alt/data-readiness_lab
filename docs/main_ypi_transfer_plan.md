# Main YPI Transfer Plan

This document explains which source-lab outputs are ready to transfer into the main YPI repo later, and which parts should remain research-only for now.

## Raw Ingestion Mapping

- `results/market_dataset_pilot_raw.json`
  This is the current source-lab raw ingestion preview.
  It already maps closely to the main YPI raw-listing ingestion shape because it keeps source name, listing URL, raw title, raw price text, field hints, parser state, and quality notes.

- `results/normalized_dataset_preview.json`
  This is the first draft of what a main-repo normalized listing-prep layer could consume.
  It adds draft canonical builder/model, numeric year, draft price, draft LOA, country, location text, duplicate-cluster suggestion, and review status.

- `results/duplicate_candidates.json`
  This is the current duplicate-review handoff layer.
  The main repo should treat these as review candidates or cluster hints, not auto-merge instructions.

## Parser Modules That Could Become Real Source Adapters

- `src/ypi_source_lab/parsers/theyachtmarket.py`
  This is the strongest current candidate for promotion into a real main-repo source adapter.
  It already parses a small proven sample with strong price, builder/model, year, location, LOA, and engine extraction.

- `src/ypi_source_lab/parsers/marine_one.py`
  This is the strongest local broker trust-anchor candidate.
  It should transfer later only after the main repo is ready to accept partial adapters with mandatory review flags, because location and engine still remain weak in raw HTTP responses.

## Field Mapping Toward Main YPI Entities

Raw source-lab outputs already point toward three future main-repo entity layers:

- Boats
  Candidate mapping:
  `canonical_builder_draft`
  `canonical_model_draft`
  `year_built_draft`
  `loa_m_draft`
  `boat_type_draft`

- Listings
  Candidate mapping:
  `source_name`
  `listing_url`
  `price_amount_draft`
  `currency_draft`
  `price_eur_draft`
  `country_draft`
  `location_text_draft`
  `data_quality_score`
  `valuation_ready_candidate`
  `review_required`

- Engines
  Candidate mapping:
  `engine_signature_draft`
  This should remain a loose text signature until the main repo adds engine normalization rules.

## Duplicate Cluster Transfer

- `duplicate_cluster_id_suggestion` should transfer as a review-oriented cluster hint.
- `duplicate_confidence` should transfer with the cluster so the main repo can prioritize human review.
- Duplicate clusters should not auto-delete, auto-merge, or auto-hide listings at transfer time.
- The main YPI repo should preserve original listing URLs and source names for every member in a cluster.

## What Still Needs Manual Review

- Any non-EUR listing that still needs FX conversion into a consistent valuation currency.
- Any record with `review_required = true`.
- Any record with `duplicate_confidence` above `none`.
- Any record where country/location is missing or weak.
- Any record where engine data is missing but later underwriting or insurance features would depend on it.

## What Remains Research-Only

- Source-readiness classifications and bounded probe logic remain source-lab concerns until a source is promoted.
- Rendering-dependent source checks remain research-only.
- Blocked `403` sources remain delayed or permission/feed/API candidates, not adapter candidates.
- Tiny parser prototypes should stay in the source lab until they are stable enough to become versioned main-repo adapters.
