# Burza Nautike Notes

- Public domain assumption for Wave 1 probing: `https://www.burzanautike.com`
- Probe targets are search-discovered public category/classified entry points.
- Field probing is limited to one discoverable detail page if raw HTML makes that safe.
- Latest result: `candidate_detail_discovery_partial`
- Homepage, `/plovila`, and `/oglasnik` returned `200`, and both `robots.txt` and `sitemap.xml` were reachable.
- The bounded detail-discovery pass found only one deeper candidate path from raw HTML, and it resolved to another classifieds/category page rather than a unique listing detail page.
- Recommendation: delay parser work for now. This source may deserve a later discovery-focused retry, but the current raw HTML sample did not prove listing-detail reachability.
- Final delayed-source decision after the Wave 2 pass: `delayed_detail_discovery`.
- Near-term recommendation: keep it in the Adriatic watchlist, but do not promote it into parser work until a stricter detail-link proof exists.
