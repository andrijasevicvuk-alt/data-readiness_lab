# Wave 2 And Delayed Source Report

This report combines a final near-term decision pass for delayed sources and a bounded Wave 2 multi-country source probe.

## Delayed Source Final Decisions

| Source | Prior Classification | Final Decision | Reason |
| --- | --- | --- | --- |
| Croatian Yachting | `candidate_accessible_needs_browser_rendering` | `rendered_adapter_candidate` | Public pages are reachable, but raw HTML still does not prove enough safe detail-link or field visibility without rendering. |
| Burza Nautike | `candidate_detail_discovery_partial` | `delayed_detail_discovery` | Public pages are reachable and regional, but the bounded raw-HTML pass still did not prove stable listing-detail URLs. |
| Yachtall | `candidate_accessible_fields_weak` | `not_worth_pursuing_now` | Accessible pages exist, but the sampled detail path collapsed back to a generic page and field evidence stayed weak. |
| Njuškalo Nautika | `candidate_requires_rendering_for_detail_links` | `blocked_do_not_bypass` | ShieldSquare challenge content appeared on the public nautical path, so the lab should stop rather than escalate into rendering or bypass behavior. |

## Wave 2 Ranking

1. Apollo Duck: `not_ready` with `9` accessible bucket(s) and best signal count `9`.
2. boats.com: `blocked_do_not_bypass` with `0` accessible bucket(s) and best signal count `0`.
3. Boatshed: `blocked_do_not_bypass` with `0` accessible bucket(s) and best signal count `0`.
4. Boatshop24: `blocked_do_not_bypass` with `0` accessible bucket(s) and best signal count `0`.
5. Botentekoop: `blocked_do_not_bypass` with `0` accessible bucket(s) and best signal count `0`.
6. YachtWorld: `blocked_do_not_bypass` with `0` accessible bucket(s) and best signal count `0`.

## Wave 2 Table

| Source | Country | Status | Detail Links | Signals | Challenge | Recommended Role |
| --- | --- | ---: | ---: | ---: | --- | --- |
| boats.com | Croatia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Slovenia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Italy | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Greece | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Turkey | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Montenegro | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Malta | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | Spain | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| boats.com | France | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Croatia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Slovenia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Italy | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Greece | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Turkey | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Montenegro | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Malta | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | Spain | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Botentekoop | France | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Croatia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Slovenia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Italy | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Greece | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Turkey | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Montenegro | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Malta | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | Spain | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshop24 | France | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Apollo Duck | Croatia | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Slovenia | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Italy | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Greece | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Turkey | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Montenegro | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Malta | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | Spain | 200 | 111 | 9 | False | `not_ready` |
| Apollo Duck | France | 200 | 111 | 9 | False | `not_ready` |
| Boatshed | Croatia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Slovenia | 200 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Italy | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Greece | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Turkey | 200 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Montenegro | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Malta | 200 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | Spain | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| Boatshed | France | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Croatia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Slovenia | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Italy | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Greece | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Turkey | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Montenegro | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Malta | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | Spain | 403 | 0 | 0 | True | `blocked_do_not_bypass` |
| YachtWorld | France | 403 | 0 | 0 | True | `blocked_do_not_bypass` |

## Near-Term Readout

- Best new reachable source in this pass: `Apollo Duck`.
- Major marketplace benchmarks from Boats Group are still returning challenge/403 behavior to the raw public probe client, so they remain unusable in the lab's non-bypass mode.
- Apollo Duck is the main accessible Wave 2 source from this pass, but it should still be judged by the quality of its country-bucket and detail-link evidence rather than by reachability alone.