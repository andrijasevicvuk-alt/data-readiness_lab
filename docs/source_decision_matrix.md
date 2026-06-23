# Source Decision Matrix

This document defines how the probe framework classifies sources during early YPI source research.

## Purpose

The classification is intentionally conservative. It is designed to answer:

1. Can we access a few public pages politely?
2. Does the source expose public discovery files such as `robots.txt` or `sitemap.xml`?
3. Does the source appear to allow or block technical access for research?

## Classification States

## `candidate_accessible`

Use when:

- The site homepage or a small number of public pages return successful HTTP responses.
- No `403` block is encountered during the small probe sample.
- The source appears publicly reachable for basic technical inspection.

Interpretation:

- The source may be technically suitable for deeper manual review.
- This is not legal approval and not production scraping approval.

## `candidate_accessible_with_limits`

Use when:

- Some public pages are reachable.
- The site is partially reachable, inconsistent, or only some public sections are exposed.
- Robots or sitemap signals suggest caution or limited discovery.

Interpretation:

- The source may still be useful, but only with a narrow scope and extra manual review.

## `candidate_accessible_fields_visible`

Use when:

- Public HTML access works.
- Listing discovery is clear enough for a tiny parser prototype.
- At least one tested detail page has a clearly stable public listing URL.
- Core listing signals such as price, year, length, title, and stable detail URLs are visible in raw HTML.

## `candidate_accessible_fields_weak`

Use when:

- Public HTML access works.
- Some field signals are present, but enough important fields are missing or inconsistent that parser work would still be fragile.

## `candidate_accessible_needs_browser_rendering`

Use when:

- Public pages load, but the raw HTML is mostly an app shell or hydration payload.
- Important listing signals are not clearly visible without browser rendering.

## `candidate_accessible_listing_discovery_unclear`

Use when:

- Public pages load.
- The site appears accessible, but raw HTML does not clearly expose a small set of stable public detail links for safe testing.

## `candidate_detail_discovery_success`

Use when:

- A bounded raw-HTML discovery pass finds one or more probable public detail pages.
- The candidate detail URLs stay public, return `200`, and look like unique listing pages rather than categories or search results.

## `candidate_detail_discovery_partial`

Use when:

- Raw HTML exposes some deeper candidate links.
- The pass proves there is navigable public structure, but the tested candidates are mixed, category-like, or not yet reliable enough to treat as clear listing details.

## `candidate_detail_discovery_failed`

Use when:

- The bounded discovery pass does not confirm any probable public detail pages.
- Tested candidates collapse into challenge pages, not-found pages, or non-detail destinations.

## `candidate_requires_rendering_for_detail_links`

Use when:

- Public pages return `200`.
- Raw HTML does not expose a safe small set of candidate detail links.
- The response looks like a shell, challenge page, or otherwise incomplete raw view where browser-visible link discovery may differ.

## `parser_prototype_success`

Use when:

- A tiny source-specific parser can extract the core raw listing fields from the small proven sample.
- The parser does not need browser tricks, bypass logic, or large crawl scope.
- The source can be considered a strong candidate for later adapter work or broader marketplace-style MVP testing.

## `parser_prototype_partial`

Use when:

- The tiny parser can extract a meaningful subset of fields from the proven sample.
- One or more important fields remain weak, missing, or only partially reliable.

## `parser_prototype_not_viable`

Use when:

- Even the tiny proven sample does not expose enough raw signal for a useful parser prototype.

## `requires_rendered_text_for_location`

Use when:

- Core public pages return `200`.
- Raw HTTP content is missing a trustworthy listing-level location signal.
- Rendered visible text exposes a listing-level location phrase that is useful for research, but not yet acceptable as the basis for production parsing in this lab.

## `blocked_403_do_not_bypass`

Use when:

- Any probed page returns HTTP `403`.

Interpretation:

- Treat the source as intentionally blocking this research agent.
- Do not use bypass techniques.
- Stop at the technical assessment stage.

## `robots_disallow_probe_targets`

Use when:

- The small set of probe targets is disallowed by `robots.txt`.

Interpretation:

- Do not continue probing those paths.
- The source may still be reviewed manually later, but it is not a current candidate for automated collection.

## `archive_not_public_or_not_found`

Use when:

- Archive-related pages were explicitly tested for a source, but no public archive entry points were found.

Interpretation:

- The archive concept exists in research scope, but there is no obvious public technical entry point.

## `temporarily_unavailable_or_error`

Use when:

- DNS, TLS, timeout, or repeated server-side errors prevent a meaningful probe.

Interpretation:

- The run was inconclusive.
- Retry later before making a final source decision.

## Decision Inputs

Each source probe should capture:

- Base URL and pages tested
- Target confidence and target-source note
- HTTP status codes
- `robots.txt` outcome
- `sitemap.xml` outcome
- Notes about archive/public discovery behavior
- Final classification

## Target Confidence Values

## `official_public_url`

Use when the target URL is confirmed from the source's own public website or public navigation.

## `search_discovered_public_url`

Use when the target was found from search or public discovery, but not yet confirmed from stronger first-party cues.

## `guessed_url`

Use when the target is still heuristic and should be treated as lower-confidence research input.

## Guardrails

- Only test a few public pages per source.
- Use a clear research user agent.
- Use slow delays between requests.
- Never treat a `403` as a challenge to overcome.
