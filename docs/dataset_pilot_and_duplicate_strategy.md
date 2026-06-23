# Dataset Pilot And Duplicate Strategy

This document explains why the current YPI source lab is moving from source readiness into a small controlled market dataset pilot.

## Why This Dataset Exists

The first purpose of the dataset pilot is to prove valuation usefulness.
That means testing whether a small, diverse market sample can already support useful price comparison, model comparison, and human-reviewed market context for boats that look commercially similar.

The same pilot can also support insurance-department tools later.
Insurance teams often need comparable listings, evidence of market asking ranges, and traceable source links when reviewing declared values, renewals, damage cases, or underwriting edge cases.

## Source Roles

- `broader_marketplace_backbone`
  The source gives wide coverage across many builders, models, and regions and can anchor the first MVP market sample.

- `local_broker_trust_anchor`
  The source gives higher-trust local broker listings and helps validate pricing and presentation quality against broader marketplace sources.

- `local_classifieds_anchor`
  The source may later add more local breadth, but still needs better detail discovery or parser confidence first.

- `delayed_source`
  The source is reachable but still depends on rendering, better discovery, or other later work before it is safe to use in the pilot.

## Why Dedupe Is Required

Market valuation records become misleading when the same yacht or very similar repeated listing appears multiple times.
This can distort price ranges, model counts, and location coverage.

Because of that, duplicate review is required before the project can claim valuation-ready records.

## Why Duplicate Candidates Are Reviewed, Not Deleted

The pilot does not auto-delete duplicates.
Instead it creates duplicate candidates for human review.

This is important because:

- near-duplicate listings can still represent distinct real boats
- brokers and marketplaces can describe the same boat differently
- prices can differ because of currency, brokerage markup, timing, or listing refreshes
- false-positive duplicate deletion would damage trust in the dataset

## Current Best Pair

- `TheYachtMarket` is the first broader marketplace backbone candidate.
- `Marine One / YachtBrokerage` is the first local broker trust-anchor candidate.

Together they form the best current controlled pilot pair.

## Next Source Expansion Plan

Revisit first:

- Croatian Yachting
- Burza Nautike
- Yachtall

Wave 2 additions later:

- boats.com
- Boatshop24
- Botentekoop
- Apollo Duck Croatia
- Boatshed Croatia

## Pilot Success Standard

The pilot succeeds if it can show:

- a traceable raw market sample from proven public pages
- useful price and boat-identity fields for valuation review
- enough cross-source structure to test duplicate-review logic
- a clear path from source research into later adapter work without depending on blocked `403` sources
