# Localized Marine Text Extraction Roadmap

This roadmap evaluates a future side-repo workflow for turning messy localized marine text into reviewed deterministic extraction rules that can later improve the main YPI dataset.

## Why This Matters For YPI

The next jump in dataset value will not come only from adding more rows.
It will come from extracting better structured meaning from the descriptive text that brokers and local classified sellers already publish.

That matters for YPI because valuation usefulness improves when a record contains more than builder, model, year, and price.
Insurance-department workflows also benefit when descriptive text can be reviewed and converted into condition, maintenance, ownership, and location signals.

Examples of useful target attributes:

- `loa_m`
- `drive_type`
- `maintenance_signals`
- `engine_service_signal`
- `hull_maintenance_signal`
- `ownership_status_hint`
- `location_text_draft`
- `condition_signal`
- `review_required`
- `extraction_confidence`

## Why Croatian And Adriatic Terminology Is Valuable

Croatian and Adriatic broker/classified text often carries practical signals that broader marketplace fields do not standardize well.
That text may describe:

- LOA using local phrase variants such as `dužina preko svega` or `duljina preko svega`
- drive systems such as `osovinski vod`, `Z pogon`, and `saildrive`
- maintenance phrases such as `obavljen servis cinkova`, `zamjena cinkova`, `antifouling napravljen`, and `generalni servis motora`
- ownership or usage clues such as `nikad u charteru` and `privatno korišten`
- location phrases such as `plovilo se nalazi u` and `vez u Splitu`

These signals can make YPI records materially more useful for:

- valuation review
- insurance checks
- maintenance/condition confidence
- ownership and charter-history hints
- Adriatic market confidence

## Why Messy Text Should Be Staged First

Messy text should not go directly into production extraction rules.
Instead, it should first be staged in a side-repo review layer so we can:

- preserve the original text evidence
- isolate ambiguous phrasing
- compare multiple localized variants
- test candidate patterns against positive and negative examples
- prevent overconfident extraction from noisy broker prose

This staging step is especially important because descriptive listing text often mixes marketing language, abbreviations, multilingual fragments, and partial specifications.

## Role Of ChatGPT Plus In Review

ChatGPT Plus can be useful during manual review as a rule-discovery assistant.
It can help reviewers:

- cluster similar phrase variants
- suggest candidate regex patterns
- propose terminology mappings
- highlight likely false positives
- translate or normalize localized marine phrasing into draft attributes

But ChatGPT Plus should not become the production parser.
The production path should stay deterministic, testable, and rerunnable.

That means:

- ChatGPT can assist with candidate discovery
- human review decides what is accepted
- accepted rules become deterministic code and fixtures
- rejected or uncertain rules stay in the side repo

## Proposed Staging Workflow

1. During manual review, capture messy or unparsed listing text blocks into a local staging file.
2. Mark useful fragments as candidate terminology examples.
3. Use manual ChatGPT-assisted review to propose regexes and mappings.
4. Review those candidate rules against positive and negative examples.
5. Keep only the accepted deterministic rules.
6. Add fixture tests before any promotion to the main YPI repo.

## Proposed Staging Schema

```json
{
  "staging_id": "example-001",
  "source_name": "Marine One",
  "listing_url": "https://example.test/listing",
  "raw_title": "Example yacht title",
  "raw_description_block": "Example messy listing text",
  "raw_specs_block": "Example raw specs text",
  "language_hint": "hr",
  "unparsed_text_segments": [
    "dužina preko svega 12.4 m",
    "obavljen servis cinkova",
    "osovinski vod"
  ],
  "suspected_terms": [
    "dužina preko svega",
    "servis cinkova",
    "osovinski vod"
  ],
  "review_status": "needs_review"
}
```

## Proposed Reviewed Rule Schema

```json
{
  "rule_id": "hr_loa_001",
  "language": "hr",
  "source_phrase_examples": [
    "dužina preko svega 12.4 m",
    "duljina preko svega 12,4 m"
  ],
  "target_attribute": "loa_m",
  "candidate_regex": "(?:dužina|duljina)\\s+preko\\s+svega\\s*[:\\-]?\\s*(\\d+(?:[\\.,]\\d+)?)\\s*m",
  "positive_examples": [
    "dužina preko svega 12.4 m",
    "duljina preko svega: 12,4 m"
  ],
  "negative_examples": [
    "dužina plovidbe 12 sati",
    "svega nekoliko sati rada"
  ],
  "extraction_confidence": "high",
  "review_status": "accepted_for_fixture_test",
  "notes": "Maps Croatian LOA phrase to loa_m after comma-to-dot normalization."
}
```

## How Candidate Rules Should Be Reviewed And Promoted

Candidate regex rules should move through a narrow review path:

1. capture and store the original phrase examples
2. propose a target attribute
3. write candidate regexes
4. test them against positive examples
5. test them against negative examples
6. confirm they do not silently overwrite stronger structured fields
7. attach confidence guidance and review signals
8. only then promote them into deterministic extraction code

## Promotion Criteria

Rules can move from this side repo into the main YPI repo only if:

- they have positive examples
- they have negative examples
- they include target attribute mapping
- they include extraction confidence
- they have fixture tests
- they do not silently overwrite structured source fields
- they produce review signals when confidence is low
- they are deterministic and rerunnable

## Proposed Future Folder Structure

Side repo future experiment:

```text
results/unparsed_text_segments.json
results/reviewed_localized_rules.json
docs/localized_marine_text_extraction_roadmap.md
tests/fixtures/localized_terms_examples.json
```

Main YPI future transfer target:

```text
services/pipeline/extract/localized_terms.py
services/pipeline/extract/rule_catalog.py
tests/fixtures/localized_terms_examples.json
tests/test_localized_terms.py
docs/localized_marine_terms_extraction.md
```

## Dataset Value Plan

To make the likely future source mix as valuable as possible:

- use marketplace sources for price range and market breadth
- use broker sources for trust, condition, maintenance, and ownership signals
- use local classifieds for private-market pricing
- use duplicate clustering before valuation-ready publication
- store price snapshots for price history
- separate price influence from confidence influence
- mark weak or missing location/ownership/engine fields for review
- do not let raw text go directly into scoring

This matters because the best dataset is not just bigger.
It is richer, more reviewable, and more explicit about confidence.

## How This Improves Valuation And Insurance Usefulness

If this workflow succeeds, YPI can convert noisy text into reviewed attributes that better support:

- valuation comparables
- condition-aware price interpretation
- engine and drive-type differentiation
- ownership/private/charter context
- maintenance history clues
- local market confidence in Adriatic listings
- insurance review and underwriting support

## Recommended Repo Boundary

This idea should begin in the side repo, not the main YPI repo.
The side repo is the right place for:

- messy text staging
- candidate regex discovery
- manual ChatGPT-assisted review
- experimental and rejected rules

Only accepted deterministic rules, fixtures, and extraction logic should later move into the main YPI repo.
