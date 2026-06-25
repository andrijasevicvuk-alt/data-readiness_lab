from __future__ import annotations

import csv
import json
import re
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType

from .field_probe import (
    LinkExtractor,
    extract_title,
    has_brand_signal,
    has_location_signal,
    has_model_signal,
    is_same_origin,
    normalize_url,
    strip_fragment,
    strip_tags,
)
from .http_client import HttpResponse, PoliteHttpClient
from .runner import SOURCES_DIR, load_module_from_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
DOCS_DIR = PROJECT_ROOT / "docs"

SOURCE_JSON_OUTPUT = RESULTS_DIR / "wave2_source_tests.json"
SOURCE_CSV_OUTPUT = RESULTS_DIR / "wave2_source_tests.csv"
FIELD_JSON_OUTPUT = RESULTS_DIR / "wave2_field_probe_results.json"
FIELD_CSV_OUTPUT = RESULTS_DIR / "wave2_field_probe_results.csv"
MARKDOWN_OUTPUT = DOCS_DIR / "wave2_and_delayed_source_report.md"

EXISTING_SOURCE_RESULTS = RESULTS_DIR / "source_tests.json"

WAVE2_SOURCE_IDS = [
    "boats_com",
    "botentekoop",
    "boatshop24",
    "apollo_duck",
    "boatshed",
    "yachtworld",
]

DELAYED_SOURCE_IDS = [
    "croatian_yachting",
    "burza_nautike",
    "yachtall",
    "njuskalo_nautika",
]

CHALLENGE_MARKERS = [
    "performing security verification",
    "access denied",
    "shieldsquare",
    "captcha",
    "verify you are human",
    "checking if the site connection is secure",
    "attention required",
    "cloudflare",
]


@dataclass(frozen=True)
class CountryBucket:
    label: str
    slug: str


COUNTRY_BUCKETS = [
    CountryBucket("Croatia", "croatia"),
    CountryBucket("Slovenia", "slovenia"),
    CountryBucket("Italy", "italy"),
    CountryBucket("Greece", "greece"),
    CountryBucket("Turkey", "turkey"),
    CountryBucket("Montenegro", "montenegro"),
    CountryBucket("Malta", "malta"),
    CountryBucket("Spain", "spain"),
    CountryBucket("France", "france"),
]


@dataclass
class Wave2SourceConfig:
    source_id: str
    source_name: str
    base_url: str
    homepage_url: str
    listing_url: str
    country_url_template: str
    target_source_note: str
    preferred_anchor_texts: list[str] = field(default_factory=list)
    detail_url_must_contain: list[str] = field(default_factory=list)
    detail_url_deny_contain: list[str] = field(default_factory=list)
    brand_keywords: list[str] = field(default_factory=list)
    location_keywords: list[str] = field(default_factory=list)
    accessible_market_role: str = "not_ready"


@dataclass
class Wave2SourceRow:
    source_name: str
    country_bucket: str
    test_url: str
    http_status: int | None
    final_url: str
    listing_count_visible: int | None
    raw_detail_links_visible: int
    sample_detail_links_tested: int
    first_detail_tested_url: str | None
    title_signal: bool
    price_signal: bool
    currency_signal: bool
    builder_model_signal: bool
    year_signal: bool
    location_signal: bool
    loa_signal: bool
    engine_signal: bool
    image_signal: bool
    blocked_or_challenge_signal: bool
    recommended_market_role: str
    notes: str = ""


def main() -> int:
    client = PoliteHttpClient(min_delay_seconds=2.0)
    configs = load_wave2_configs()
    rows, field_rows = run_wave2_probes(client, configs)
    delayed_decisions = build_delayed_source_decisions()
    write_outputs(rows, field_rows, delayed_decisions)
    print(f"Wrote {SOURCE_JSON_OUTPUT}")
    print(f"Wrote {SOURCE_CSV_OUTPUT}")
    print(f"Wrote {FIELD_JSON_OUTPUT}")
    print(f"Wrote {FIELD_CSV_OUTPUT}")
    print(f"Wrote {MARKDOWN_OUTPUT}")
    return 0


def load_wave2_configs() -> list[Wave2SourceConfig]:
    configs: list[Wave2SourceConfig] = []
    for source_id in WAVE2_SOURCE_IDS:
        probe_path = SOURCES_DIR / source_id / "probe.py"
        module = load_module_from_path(probe_path)
        if not hasattr(module, "get_wave2_source_config"):
            raise RuntimeError(f"Wave 2 probe file missing get_wave2_source_config(): {probe_path}")
        config = module.get_wave2_source_config()
        configs.append(config)
    return configs


def run_wave2_probes(
    client: PoliteHttpClient,
    configs: list[Wave2SourceConfig],
) -> tuple[list[Wave2SourceRow], list[dict[str, object]]]:
    rows: list[Wave2SourceRow] = []
    field_rows: list[dict[str, object]] = []

    for config in configs:
        homepage_response = client.get(config.homepage_url, max_bytes=250_000)
        listing_response = client.get(config.listing_url, max_bytes=300_000)
        source_blocked = is_blocked_or_challenge(homepage_response) or is_blocked_or_challenge(listing_response)

        for country in COUNTRY_BUCKETS:
            test_url = build_country_url(config, country)
            response = client.get(test_url, max_bytes=300_000)

            detail_rows_for_bucket: list[dict[str, object]] = []
            blocked = source_blocked or is_blocked_or_challenge(response)
            if blocked or response.status_code != 200:
                row = Wave2SourceRow(
                    source_name=config.source_name,
                    country_bucket=country.label,
                    test_url=test_url,
                    http_status=response.status_code,
                    final_url=response.final_url,
                    listing_count_visible=None,
                    raw_detail_links_visible=0,
                    sample_detail_links_tested=0,
                    first_detail_tested_url=None,
                    title_signal=False,
                    price_signal=False,
                    currency_signal=False,
                    builder_model_signal=False,
                    year_signal=False,
                    location_signal=False,
                    loa_signal=False,
                    engine_signal=False,
                    image_signal=False,
                    blocked_or_challenge_signal=blocked,
                    recommended_market_role="blocked_do_not_bypass" if blocked else "not_ready",
                    notes=blocked_notes(response),
                )
                rows.append(row)
                field_rows.append(
                    build_field_row(
                        row=row,
                        page_type="country_bucket",
                        tested_url=test_url,
                        detail_tested_url=None,
                        notes=row.notes,
                    )
                )
                continue

            page_signals = analyze_page_signals(config, response, country)
            detail_urls = discover_detail_urls_for_wave2(config, response)
            first_detail_tested_url: str | None = None

            combined = dict(page_signals)
            detail_test_count = 0
            for detail_url in detail_urls[:1]:
                detail_response = client.get(detail_url, max_bytes=250_000)
                detail_test_count += 1
                first_detail_tested_url = detail_url
                detail_signals = analyze_page_signals(config, detail_response, country)
                combined = combine_signals(combined, detail_signals)
                detail_rows_for_bucket.append(
                    build_field_row(
                        row=None,
                        page_type="detail",
                        tested_url=test_url,
                        detail_tested_url=detail_url,
                        notes="detail sample fetched",
                        source_name=config.source_name,
                        country_bucket=country.label,
                        http_status=detail_response.status_code,
                        final_url=detail_response.final_url,
                        signals=detail_signals,
                        blocked_or_challenge_signal=is_blocked_or_challenge(detail_response),
                    )
                )

            role = determine_market_role(config, combined, len(detail_urls), detail_test_count)
            row = Wave2SourceRow(
                source_name=config.source_name,
                country_bucket=country.label,
                test_url=test_url,
                http_status=response.status_code,
                final_url=response.final_url,
                listing_count_visible=estimate_listing_count(response.body, len(detail_urls)),
                raw_detail_links_visible=len(detail_urls),
                sample_detail_links_tested=detail_test_count,
                first_detail_tested_url=first_detail_tested_url,
                title_signal=combined["title_signal"],
                price_signal=combined["price_signal"],
                currency_signal=combined["currency_signal"],
                builder_model_signal=combined["builder_model_signal"],
                year_signal=combined["year_signal"],
                location_signal=combined["location_signal"],
                loa_signal=combined["loa_signal"],
                engine_signal=combined["engine_signal"],
                image_signal=combined["image_signal"],
                blocked_or_challenge_signal=False,
                recommended_market_role=role,
                notes=page_signals["notes"],
            )
            rows.append(row)
            field_rows.append(
                build_field_row(
                    row=row,
                    page_type="country_bucket",
                    tested_url=test_url,
                    detail_tested_url=None,
                    notes=page_signals["notes"],
                )
            )
            field_rows.extend(detail_rows_for_bucket)

    return postprocess_wave2_rows(rows), field_rows


def build_country_url(config: Wave2SourceConfig, country: CountryBucket) -> str:
    return config.country_url_template.format(
        slug=country.slug,
        label=country.label,
        query=urllib.parse.quote(country.label),
    )


def analyze_page_signals(
    config: Wave2SourceConfig,
    response: HttpResponse,
    country: CountryBucket,
) -> dict[str, object]:
    body = response.body or ""
    normalized_text = " ".join(strip_tags(body).split())
    lower_text = normalized_text.lower()
    title = extract_title(body)
    image_signal = bool(re.search(r"<img\b", body, flags=re.IGNORECASE)) or "og:image" in body.lower()
    price_signal = bool(
        re.search(r"(\u20ac|\bEUR\b|\$|\bUSD\b|\bGBP\b)\s*[0-9][0-9., ]+", normalized_text)
        or re.search(r'"price"\s*:\s*"?(?:[0-9][0-9., ]+)"?', body, flags=re.IGNORECASE)
    )
    currency_signal = bool(
        re.search(r"(\u20ac|\bEUR\b|\$|\bUSD\b|\bGBP\b)", normalized_text)
        or re.search(r'priceCurrency"\s*:\s*"?(EUR|USD|GBP)"?', body, flags=re.IGNORECASE)
    )
    builder_signal = has_brand_signal(normalized_text, config.brand_keywords)
    model_signal = has_model_signal(normalized_text, config.brand_keywords)
    year_signal = bool(re.search(r"\b(19|20)\d{2}\b", normalized_text))
    location_signal = has_location_signal(lower_text, config.location_keywords + [country.label])
    loa_signal = bool(
        re.search(r"\b(loa|length)\b", lower_text)
        or re.search(r"\b\d{1,2}(?:[.,]\d{1,2})?\s?(m|ft)\b", normalized_text)
    )
    engine_signal = bool(
        re.search(r"\b(engine|engines|hp|kw|yanmar|volvo|mercury|diesel|petrol|gasoline)\b", lower_text)
    )

    notes = []
    if title:
        notes.append(f"title={title[:100]}")
    if response.final_url != response.url:
        notes.append("redirected")

    return {
        "title_signal": bool(title),
        "price_signal": price_signal,
        "currency_signal": currency_signal,
        "builder_model_signal": builder_signal and model_signal,
        "year_signal": year_signal,
        "location_signal": location_signal,
        "loa_signal": loa_signal,
        "engine_signal": engine_signal,
        "image_signal": image_signal,
        "notes": " | ".join(notes),
    }


def combine_signals(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    return {
        "title_signal": bool(left["title_signal"] or right["title_signal"]),
        "price_signal": bool(left["price_signal"] or right["price_signal"]),
        "currency_signal": bool(left["currency_signal"] or right["currency_signal"]),
        "builder_model_signal": bool(left["builder_model_signal"] or right["builder_model_signal"]),
        "year_signal": bool(left["year_signal"] or right["year_signal"]),
        "location_signal": bool(left["location_signal"] or right["location_signal"]),
        "loa_signal": bool(left["loa_signal"] or right["loa_signal"]),
        "engine_signal": bool(left["engine_signal"] or right["engine_signal"]),
        "image_signal": bool(left["image_signal"] or right["image_signal"]),
        "notes": " | ".join(part for part in [str(left.get("notes", "")), str(right.get("notes", ""))] if part),
    }


def discover_detail_urls_for_wave2(config: Wave2SourceConfig, response: HttpResponse) -> list[str]:
    if response.status_code != 200 or not response.body:
        return []

    parser = LinkExtractor()
    parser.feed(response.body)
    preferred_texts = [item.lower() for item in config.preferred_anchor_texts]

    urls: list[str] = []
    seen: set[str] = set()
    for link in parser.links:
        href = link.get("href", "").strip()
        text = link.get("text", "").strip().lower()
        absolute_url = normalize_url(response.url, href)
        if not absolute_url:
            continue
        if not is_same_origin(response.url, absolute_url):
            continue

        cleaned_url = strip_fragment(absolute_url)
        if cleaned_url in seen:
            continue
        if any(fragment.lower() in cleaned_url.lower() for fragment in config.detail_url_deny_contain):
            continue

        text_match = any(candidate in text for candidate in preferred_texts)
        url_match = any(candidate.lower() in cleaned_url.lower() for candidate in config.detail_url_must_contain)
        if not text_match and not url_match:
            continue

        seen.add(cleaned_url)
        urls.append(cleaned_url)
    return urls


def estimate_listing_count(raw_html: str, discovered_detail_links: int) -> int | None:
    text = " ".join(strip_tags(raw_html).split())
    match = re.search(r"\b([0-9]{1,4}(?:,[0-9]{3})?)\s+(?:boats?|yachts?|results?|listings?)\b", text, flags=re.IGNORECASE)
    if match:
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            pass
    return discovered_detail_links or None


def is_blocked_or_challenge(response: HttpResponse) -> bool:
    if response.status_code == 403:
        return True
    body = (response.body or "").lower()
    title = extract_title(response.body or "").lower()
    combined = f"{title} {body}"
    return any(marker in combined for marker in CHALLENGE_MARKERS)


def blocked_notes(response: HttpResponse) -> str:
    if response.status_code == 403:
        return "HTTP 403 or challenge stop signal"
    if is_blocked_or_challenge(response):
        return "challenge-like public page detected"
    if response.status_code and response.status_code >= 400:
        return f"HTTP {response.status_code}"
    return response.error or ""


def determine_market_role(
    config: Wave2SourceConfig,
    signals: dict[str, object],
    raw_detail_links_visible: int,
    sample_detail_links_tested: int,
) -> str:
    if raw_detail_links_visible <= 0:
        return "not_ready"

    positive = sum(
        [
            bool(signals["title_signal"]),
            bool(signals["price_signal"]),
            bool(signals["currency_signal"]),
            bool(signals["builder_model_signal"]),
            bool(signals["year_signal"]),
            bool(signals["location_signal"]),
            bool(signals["loa_signal"]),
            bool(signals["engine_signal"]),
            bool(signals["image_signal"]),
        ]
    )
    if sample_detail_links_tested > 0 and positive >= 6:
        return config.accessible_market_role
    if positive >= 5:
        return config.accessible_market_role
    return "not_ready"


def postprocess_wave2_rows(rows: list[Wave2SourceRow]) -> list[Wave2SourceRow]:
    by_source: dict[str, list[Wave2SourceRow]] = {}
    for row in rows:
        by_source.setdefault(row.source_name, []).append(row)

    apollo_rows = by_source.get("Apollo Duck", [])
    accessible_apollo_rows = [
        row for row in apollo_rows if row.http_status == 200 and not row.blocked_or_challenge_signal
    ]
    if accessible_apollo_rows:
        first_detail_urls = {row.first_detail_tested_url for row in accessible_apollo_rows if row.first_detail_tested_url}
        listing_counts = {row.listing_count_visible for row in accessible_apollo_rows}
        generic_titles = all(
            "title=Boats for sale, used boats, new boat sales, free photo ads - Apollo Duck" in row.notes
            for row in accessible_apollo_rows
        )
        if generic_titles and len(first_detail_urls) == 1 and len(listing_counts) == 1:
            for row in accessible_apollo_rows:
                row.recommended_market_role = "not_ready"
                extra_note = "country path behaved like a generic fallback page"
                row.notes = f"{row.notes} | {extra_note}" if row.notes else extra_note

    return rows


def build_field_row(
    *,
    row: Wave2SourceRow | None,
    page_type: str,
    tested_url: str,
    detail_tested_url: str | None,
    notes: str,
    source_name: str | None = None,
    country_bucket: str | None = None,
    http_status: int | None = None,
    final_url: str | None = None,
    signals: dict[str, object] | None = None,
    blocked_or_challenge_signal: bool | None = None,
) -> dict[str, object]:
    base_signals = signals or {
        "title_signal": row.title_signal if row else False,
        "price_signal": row.price_signal if row else False,
        "currency_signal": row.currency_signal if row else False,
        "builder_model_signal": row.builder_model_signal if row else False,
        "year_signal": row.year_signal if row else False,
        "location_signal": row.location_signal if row else False,
        "loa_signal": row.loa_signal if row else False,
        "engine_signal": row.engine_signal if row else False,
        "image_signal": row.image_signal if row else False,
    }
    return {
        "source_name": source_name or (row.source_name if row else ""),
        "country_bucket": country_bucket or (row.country_bucket if row else ""),
        "page_type": page_type,
        "tested_url": tested_url,
        "detail_tested_url": detail_tested_url or "",
        "http_status": http_status if http_status is not None else (row.http_status if row else None),
        "final_url": final_url if final_url is not None else (row.final_url if row else ""),
        "title_signal": base_signals["title_signal"],
        "price_signal": base_signals["price_signal"],
        "currency_signal": base_signals["currency_signal"],
        "builder_model_signal": base_signals["builder_model_signal"],
        "year_signal": base_signals["year_signal"],
        "location_signal": base_signals["location_signal"],
        "loa_signal": base_signals["loa_signal"],
        "engine_signal": base_signals["engine_signal"],
        "image_signal": base_signals["image_signal"],
        "blocked_or_challenge_signal": (
            blocked_or_challenge_signal
            if blocked_or_challenge_signal is not None
            else (row.blocked_or_challenge_signal if row else False)
        ),
        "notes": notes,
    }


def build_delayed_source_decisions() -> list[dict[str, str]]:
    current_results = json.loads(EXISTING_SOURCE_RESULTS.read_text(encoding="utf-8"))
    by_id = {item["source_id"]: item for item in current_results}

    decisions: list[dict[str, str]] = []
    for source_id in DELAYED_SOURCE_IDS:
        item = by_id[source_id]
        decision, reason = map_delayed_decision(item)
        decisions.append(
            {
                "source_id": source_id,
                "source_name": item["source_name"],
                "current_classification": item["classification"],
                "final_decision": decision,
                "reason": reason,
            }
        )
    return decisions


def map_delayed_decision(item: dict) -> tuple[str, str]:
    source_id = item["source_id"]
    classification = item["classification"]

    if source_id == "croatian_yachting":
        return (
            "rendered_adapter_candidate",
            "Public pages are reachable, but raw HTML still does not prove enough safe detail-link or field visibility without rendering.",
        )
    if source_id == "burza_nautike":
        return (
            "delayed_detail_discovery",
            "Public pages are reachable and regional, but the bounded raw-HTML pass still did not prove stable listing-detail URLs.",
        )
    if source_id == "yachtall":
        return (
            "not_worth_pursuing_now",
            "Accessible pages exist, but the sampled detail path collapsed back to a generic page and field evidence stayed weak.",
        )
    if source_id == "njuskalo_nautika":
        return (
            "blocked_do_not_bypass",
            "ShieldSquare challenge content appeared on the public nautical path, so the lab should stop rather than escalate into rendering or bypass behavior.",
        )

    if classification == "blocked_403_do_not_bypass":
        return ("blocked_do_not_bypass", "Public probing returned a stop signal.")
    return ("not_worth_pursuing_now", "No safe near-term path was proven.")


def rank_wave2_sources(rows: list[Wave2SourceRow]) -> list[dict[str, object]]:
    by_source: dict[str, list[Wave2SourceRow]] = {}
    for row in rows:
        by_source.setdefault(row.source_name, []).append(row)

    ranked: list[dict[str, object]] = []
    for source_name, source_rows in by_source.items():
        accessible_rows = [row for row in source_rows if not row.blocked_or_challenge_signal and row.http_status == 200]
        positive_signal_count = max(
            (
                sum(
                    [
                        row.title_signal,
                        row.price_signal,
                        row.currency_signal,
                        row.builder_model_signal,
                        row.year_signal,
                        row.location_signal,
                        row.loa_signal,
                        row.engine_signal,
                        row.image_signal,
                    ]
                )
                for row in source_rows
            ),
            default=0,
        )
        recommended_roles = {row.recommended_market_role for row in source_rows}
        top_role = next(
            (
                role
                for role in [
                    "broader_marketplace_backbone",
                    "mediterranean_expansion_source",
                    "adriatic_regional_source",
                    "slovenia_neighbor_source",
                    "local_broker_trust_anchor",
                    "local_classifieds_anchor",
                    "permission_or_feed_candidate",
                    "blocked_do_not_bypass",
                    "not_ready",
                ]
                if role in recommended_roles
            ),
            "not_ready",
        )
        score = len(accessible_rows) * 10 + positive_signal_count
        if top_role == "blocked_do_not_bypass":
            score = -1

        ranked.append(
            {
                "source_name": source_name,
                "accessible_bucket_count": len(accessible_rows),
                "best_signal_count": positive_signal_count,
                "top_role": top_role,
                "score": score,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["source_name"].lower()))
    return ranked


def write_outputs(
    rows: list[Wave2SourceRow],
    field_rows: list[dict[str, object]],
    delayed_decisions: list[dict[str, str]],
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    ranked_sources = rank_wave2_sources(rows)
    source_payload = {
        "row_count": len(rows),
        "source_ranking": ranked_sources,
        "rows": [asdict(row) for row in rows],
    }
    SOURCE_JSON_OUTPUT.write_text(json.dumps(source_payload, indent=2), encoding="utf-8")

    with SOURCE_CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(Wave2SourceRow.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    field_payload = {
        "row_count": len(field_rows),
        "rows": field_rows,
    }
    FIELD_JSON_OUTPUT.write_text(json.dumps(field_payload, indent=2), encoding="utf-8")
    with FIELD_CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(field_rows[0].keys()) if field_rows else [
            "source_name",
            "country_bucket",
            "page_type",
            "tested_url",
            "detail_tested_url",
            "http_status",
            "final_url",
            "title_signal",
            "price_signal",
            "currency_signal",
            "builder_model_signal",
            "year_signal",
            "location_signal",
            "loa_signal",
            "engine_signal",
            "image_signal",
            "blocked_or_challenge_signal",
            "notes",
        ])
        writer.writeheader()
        writer.writerows(field_rows)

    MARKDOWN_OUTPUT.write_text(build_markdown_report(rows, ranked_sources, delayed_decisions), encoding="utf-8")


def build_markdown_report(
    rows: list[Wave2SourceRow],
    ranked_sources: list[dict[str, object]],
    delayed_decisions: list[dict[str, str]],
) -> str:
    lines = [
        "# Wave 2 And Delayed Source Report",
        "",
        "This report combines a final near-term decision pass for delayed sources and a bounded Wave 2 multi-country source probe.",
        "",
        "## Delayed Source Final Decisions",
        "",
        "| Source | Prior Classification | Final Decision | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for item in delayed_decisions:
        lines.append(
            f"| {item['source_name']} | `{item['current_classification']}` | `{item['final_decision']}` | {item['reason']} |"
        )

    lines.extend(["", "## Wave 2 Ranking", ""])
    for index, item in enumerate(ranked_sources, start=1):
        lines.append(
            f"{index}. {item['source_name']}: `{item['top_role']}` with `{item['accessible_bucket_count']}` accessible bucket(s) and best signal count `{item['best_signal_count']}`."
        )

    lines.extend(
        [
            "",
            "## Wave 2 Table",
            "",
            "| Source | Country | Status | Detail Links | Signals | Challenge | Recommended Role |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in rows:
        signal_count = sum(
            [
                row.title_signal,
                row.price_signal,
                row.currency_signal,
                row.builder_model_signal,
                row.year_signal,
                row.location_signal,
                row.loa_signal,
                row.engine_signal,
                row.image_signal,
            ]
        )
        lines.append(
            f"| {row.source_name} | {row.country_bucket} | {row.http_status if row.http_status is not None else 'n/a'} | "
            f"{row.raw_detail_links_visible} | {signal_count} | {row.blocked_or_challenge_signal} | `{row.recommended_market_role}` |"
        )

    lines.extend(["", "## Near-Term Readout", ""])
    if ranked_sources:
        top_source = ranked_sources[0]["source_name"]
        lines.append(f"- Best new reachable source in this pass: `{top_source}`.")
    lines.append(
        "- Major marketplace benchmarks from Boats Group are still returning challenge/403 behavior to the raw public probe client, so they remain unusable in the lab's non-bypass mode."
    )
    lines.append(
        "- Apollo Duck is the main accessible Wave 2 source from this pass, but it should still be judged by the quality of its country-bucket and detail-link evidence rather than by reachability alone."
    )
    return "\n".join(lines)
