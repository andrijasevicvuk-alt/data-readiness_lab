# Croatian Yachting Notes

- Public site used for probing: `https://www.croatia-yachting.hr/en`
- Corrected public sales targets:
- `https://www.croatia-yachting.hr/en/yachts-for-sale`
- `https://www.croatia-yachting.hr/en/yachts-for-sale/used-boats`
- These targets were taken from live public navigation instead of guessed slugs.
- Field probe result: `candidate_accessible_needs_browser_rendering`
- The homepage and used-boats page returned `200`, and raw HTML exposed some coarse signals such as title, year-like values, location-like text, and structured-data markers.
- The raw listing HTML did not expose a small set of public detail-page URLs that could be safely followed in this probe step.
- No clear asking-price, currency, length, or image-card signals were confirmed from the tested raw HTML.
- One bounded rendered-text check on the public used-boats page still did not confirm a listing-level location phrase such as `docked in Croatia`.
- Conclusion for now: publicly reachable, but not ready for a tiny raw-HTML parser prototype without browser-rendered discovery or another clearer public listing feed.
