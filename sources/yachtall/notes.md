# Yachtall Notes

- Public domain assumption for Wave 1 probing: `https://www.yachtall.com/en`
- Probe scope is limited to homepage plus a couple of public listing entry points.
- Field probing is capped to a single discoverable detail page if raw HTML links make that safe.
- Latest result: `candidate_accessible_fields_weak`
- Public pages returned `200`, but the one discovered "detail" URL collapsed back to `https://www.yachtall.com` instead of a clearly stable listing URL.
- Follow-up should wait for stronger raw-detail discovery before any parser prototype work.
- Final delayed-source decision after the Wave 2 pass: `not_worth_pursuing_now`.
- Near-term recommendation: keep it out of the MVP source queue unless the site later exposes a much clearer public detail flow.
