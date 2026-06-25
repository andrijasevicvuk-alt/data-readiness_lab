# Source Readiness Report

This report consolidates the current access, discovery, rendering, and parser evidence across all tested sources.

## Wave 2 Follow-Up

- A later bounded Wave 2 pass did not produce a stronger new backbone source than `TheYachtMarket`.
- `boats.com`, `Boatshop24`, `Botentekoop`, `Boatshed`, and `YachtWorld` returned raw-probe challenge or `403` behavior and should remain blocked in this lab.
- `Apollo Duck` was reachable, but its tested country paths behaved like generic fallback pages rather than clearly distinct country-result buckets, so it remains `not_ready`.
- Delayed-source finalization from the Wave 2 pass:
  `Croatian Yachting` -> `rendered_adapter_candidate`
  `Burza Nautike` -> `delayed_detail_discovery`
  `Yachtall` -> `not_worth_pursuing_now`
  `Njuškalo Nautika` -> `blocked_do_not_bypass`

## Current Best Pair

- TheYachtMarket is the first broader marketplace backbone candidate.
- Marine One is the first local broker trust-anchor candidate.
- Boat24 is not required for MVP if TheYachtMarket remains stable.
- Boat24 may still be useful later through permission/feed/API access or future research.

## Source Ranking

1. TheYachtMarket: `parser_prototype_success`; role `broader_marketplace_backbone`; next `Promote to adapter candidate #1 and use as the first broader marketplace backbone.`
2. Marine One: `parser_prototype_partial`; role `local_broker_trust_anchor`; next `Promote to adapter candidate #2 and harden location/engine only within current safe scope.`
3. Croatian Yachting: `candidate_accessible_needs_browser_rendering`; role `delayed_rendering_candidate`; next `Delay until a small rendering-aware discovery step is explicitly approved.`
4. Njuškalo Nautika: `candidate_requires_rendering_for_detail_links`; role `delayed_rendering_candidate`; next `Delay; only revisit if a safe rendering-based link-discovery check is later justified.`
5. Burza Nautike: `candidate_detail_discovery_partial`; role `local_classifieds_anchor`; next `Delay parser work; retry only with a tiny stricter detail-discovery pass later.`
6. Yachtall: `candidate_accessible_fields_weak`; role `not_ready`; next `Delay until stable public detail-page evidence is proven.`
7. Band of Boats: `blocked_403_do_not_bypass`; role `blocked_do_not_bypass`; next `Hold; do not bypass. Revisit only with permission/feed/API access.`
8. Boat24: `blocked_403_do_not_bypass`; role `blocked_do_not_bypass`; next `Do not use for MVP; revisit only through permission/feed/API or future research.`
9. Boat24 Archives: `blocked_403_do_not_bypass`; role `blocked_do_not_bypass`; next `Hold; do not bypass. Revisit only with permission/feed/API access.`
10. iNautia: `blocked_403_do_not_bypass`; role `blocked_do_not_bypass`; next `Hold; do not bypass. Revisit only with permission/feed/API access.`
11. TopBoats: `blocked_403_do_not_bypass`; role `blocked_do_not_bypass`; next `Hold; do not bypass. Revisit only with permission/feed/API access.`

## Table

| Source | Final Classification | Role Candidate | Parser | Parsed Sample | Location | Engine | Rendering Required | Next Action |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| TheYachtMarket | `parser_prototype_success` | `broader_marketplace_backbone` | `parser_prototype_success` | 3 | parsed_strong | parsed_strong | no | Promote to adapter candidate #1 and use as the first broader marketplace backbone. |
| Marine One | `parser_prototype_partial` | `local_broker_trust_anchor` | `parser_prototype_partial` | 4 | missing | missing | partial_for_location | Promote to adapter candidate #2 and harden location/engine only within current safe scope. |
| Croatian Yachting | `candidate_accessible_needs_browser_rendering` | `delayed_rendering_candidate` | `not_run` | 0 | signal_visible | signal_visible | yes | Delay until a small rendering-aware discovery step is explicitly approved. |
| Njuškalo Nautika | `candidate_requires_rendering_for_detail_links` | `delayed_rendering_candidate` | `not_run` | 0 | signal_visible | missing | yes | Delay; only revisit if a safe rendering-based link-discovery check is later justified. |
| Burza Nautike | `candidate_detail_discovery_partial` | `local_classifieds_anchor` | `not_run` | 0 | signal_partial | signal_partial | no | Delay parser work; retry only with a tiny stricter detail-discovery pass later. |
| Yachtall | `candidate_accessible_fields_weak` | `not_ready` | `not_run` | 0 | signal_visible | signal_visible | no | Delay until stable public detail-page evidence is proven. |
| Band of Boats | `blocked_403_do_not_bypass` | `blocked_do_not_bypass` | `not_run` | 0 | not_tested | not_tested | no | Hold; do not bypass. Revisit only with permission/feed/API access. |
| Boat24 | `blocked_403_do_not_bypass` | `blocked_do_not_bypass` | `not_run` | 0 | not_tested | not_tested | no | Do not use for MVP; revisit only through permission/feed/API or future research. |
| Boat24 Archives | `blocked_403_do_not_bypass` | `blocked_do_not_bypass` | `not_run` | 0 | not_tested | not_tested | no | Hold; do not bypass. Revisit only with permission/feed/API access. |
| iNautia | `blocked_403_do_not_bypass` | `blocked_do_not_bypass` | `not_run` | 0 | not_tested | not_tested | no | Hold; do not bypass. Revisit only with permission/feed/API access. |
| TopBoats | `blocked_403_do_not_bypass` | `blocked_do_not_bypass` | `not_run` | 0 | not_tested | not_tested | no | Hold; do not bypass. Revisit only with permission/feed/API access. |

## Per Source

### TheYachtMarket

- Access status: `reachable_public_200`
- Final classification: `parser_prototype_success`
- Role candidate: `broader_marketplace_backbone`
- Detail discovery: `probable_3`
- Parser status: `parser_prototype_success` with sample count `3`
- Field summary: title `parsed_strong`, price `parsed_strong`, currency `parsed_strong`, builder/model `parsed_strong`, year `parsed_strong`, location `parsed_strong`, LOA `parsed_strong`, engine `parsed_strong`, image `parsed_strong`
- Rendering required: `no`
- Blocker summary: Core parser fields are strong; broker field remains weak or missing.
- Recommended next action: Promote to adapter candidate #1 and use as the first broader marketplace backbone.

### Marine One

- Access status: `reachable_public_200`
- Final classification: `parser_prototype_partial`
- Role candidate: `local_broker_trust_anchor`
- Detail discovery: `not_run`
- Parser status: `parser_prototype_partial` with sample count `4`
- Field summary: title `parsed_strong`, price `parsed_strong`, currency `parsed_strong`, builder/model `parsed_strong`, year `parsed_strong`, location `missing`, LOA `parsed_strong`, engine `missing`, image `parsed_strong`
- Rendering required: `partial_for_location`
- Blocker summary: Core fields parse, but important fields remain weak or missing.
- Recommended next action: Promote to adapter candidate #2 and harden location/engine only within current safe scope.

### Croatian Yachting

- Access status: `reachable_public_200`
- Final classification: `candidate_accessible_needs_browser_rendering`
- Role candidate: `delayed_rendering_candidate`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `signal_visible`, price `missing`, currency `missing`, builder/model `signal_partial`, year `signal_visible`, location `signal_visible`, LOA `missing`, engine `signal_visible`, image `missing`
- Rendering required: `yes`
- Blocker summary: Raw HTML discovery is incomplete; browser-visible rendering likely needed.
- Recommended next action: Delay until a small rendering-aware discovery step is explicitly approved.

### Njuškalo Nautika

- Access status: `reachable_public_200`
- Final classification: `candidate_requires_rendering_for_detail_links`
- Role candidate: `delayed_rendering_candidate`
- Detail discovery: `no_candidates_in_raw_html`
- Parser status: `not_run` with sample count `0`
- Field summary: title `signal_visible`, price `missing`, currency `signal_partial`, builder/model `signal_partial`, year `signal_visible`, location `signal_visible`, LOA `signal_visible`, engine `missing`, image `signal_visible`
- Rendering required: `yes`
- Blocker summary: Raw HTML discovery is incomplete; browser-visible rendering likely needed.
- Recommended next action: Delay; only revisit if a safe rendering-based link-discovery check is later justified.

### Burza Nautike

- Access status: `reachable_public_200`
- Final classification: `candidate_detail_discovery_partial`
- Role candidate: `local_classifieds_anchor`
- Detail discovery: `tested_none_probable`
- Parser status: `not_run` with sample count `0`
- Field summary: title `signal_visible`, price `missing`, currency `signal_partial`, builder/model `signal_partial`, year `signal_visible`, location `signal_partial`, LOA `signal_partial`, engine `signal_partial`, image `signal_partial`
- Rendering required: `no`
- Blocker summary: Deeper links were found, but they still resolved to category-like pages.
- Recommended next action: Delay parser work; retry only with a tiny stricter detail-discovery pass later.

### Yachtall

- Access status: `reachable_public_200`
- Final classification: `candidate_accessible_fields_weak`
- Role candidate: `not_ready`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `signal_visible`, price `signal_visible`, currency `signal_visible`, builder/model `signal_visible`, year `signal_visible`, location `signal_visible`, LOA `signal_visible`, engine `signal_visible`, image `signal_visible`
- Rendering required: `no`
- Blocker summary: Signals exist, but stable public detail-page evidence is still weak.
- Recommended next action: Delay until stable public detail-page evidence is proven.

### Band of Boats

- Access status: `blocked`
- Final classification: `blocked_403_do_not_bypass`
- Role candidate: `blocked_do_not_bypass`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `not_tested`, price `not_tested`, currency `not_tested`, builder/model `not_tested`, year `not_tested`, location `not_tested`, LOA `not_tested`, engine `not_tested`, image `not_tested`
- Rendering required: `no`
- Blocker summary: HTTP 403 stop signal; do not bypass.
- Recommended next action: Hold; do not bypass. Revisit only with permission/feed/API access.

### Boat24

- Access status: `blocked`
- Final classification: `blocked_403_do_not_bypass`
- Role candidate: `blocked_do_not_bypass`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `not_tested`, price `not_tested`, currency `not_tested`, builder/model `not_tested`, year `not_tested`, location `not_tested`, LOA `not_tested`, engine `not_tested`, image `not_tested`
- Rendering required: `no`
- Blocker summary: HTTP 403 stop signal; do not bypass.
- Recommended next action: Do not use for MVP; revisit only through permission/feed/API or future research.

### Boat24 Archives

- Access status: `blocked`
- Final classification: `blocked_403_do_not_bypass`
- Role candidate: `blocked_do_not_bypass`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `not_tested`, price `not_tested`, currency `not_tested`, builder/model `not_tested`, year `not_tested`, location `not_tested`, LOA `not_tested`, engine `not_tested`, image `not_tested`
- Rendering required: `no`
- Blocker summary: HTTP 403 stop signal; do not bypass.
- Recommended next action: Hold; do not bypass. Revisit only with permission/feed/API access.

### iNautia

- Access status: `blocked`
- Final classification: `blocked_403_do_not_bypass`
- Role candidate: `blocked_do_not_bypass`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `not_tested`, price `not_tested`, currency `not_tested`, builder/model `not_tested`, year `not_tested`, location `not_tested`, LOA `not_tested`, engine `not_tested`, image `not_tested`
- Rendering required: `no`
- Blocker summary: HTTP 403 stop signal; do not bypass.
- Recommended next action: Hold; do not bypass. Revisit only with permission/feed/API access.

### TopBoats

- Access status: `blocked`
- Final classification: `blocked_403_do_not_bypass`
- Role candidate: `blocked_do_not_bypass`
- Detail discovery: `not_run`
- Parser status: `not_run` with sample count `0`
- Field summary: title `not_tested`, price `not_tested`, currency `not_tested`, builder/model `not_tested`, year `not_tested`, location `not_tested`, LOA `not_tested`, engine `not_tested`, image `not_tested`
- Rendering required: `no`
- Blocker summary: HTTP 403 stop signal; do not bypass.
- Recommended next action: Hold; do not bypass. Revisit only with permission/feed/API access.
