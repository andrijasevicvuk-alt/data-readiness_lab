from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..http_client import HttpResponse, PoliteHttpClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_TESTS_PATH = PROJECT_ROOT / "results" / "source_tests.json"
JSON_OUTPUT = PROJECT_ROOT / "results" / "marine_one_parser_sample.json"
CSV_OUTPUT = PROJECT_ROOT / "results" / "marine_one_parser_sample.csv"
SOURCE_NAME = "Marine One / YachtBrokerage"
LISTING_PAGE_URL = "https://www.yachtbrokerage.eu/boats-for-sale"
REGRESSION_DETAIL_URLS = [
    "https://www.yachtbrokerage.eu/marine-one-brokerage/fountaine-pajot-astrea-42/code-(1051)/2025",
]
ASTREA_42_URL = REGRESSION_DETAIL_URLS[0]


@dataclass
class MarineOneParsedListing:
    source_name: str
    listing_url: str
    raw_title: str | None
    raw_price_text: str | None
    currency_hint: str | None
    builder_hint: str | None
    model_hint: str | None
    year_hint: str | None
    location_hint: str | None
    location_evidence_source: str | None
    location_parser_note: str
    loa_hint: str | None
    engine_hint: str | None
    engine_evidence_source: str | None
    engine_parser_note: str
    image_present: bool
    structured_data_present: bool
    price_parse_confidence: str
    year_parse_confidence: str
    model_parse_confidence: str
    location_parse_confidence: str
    loa_parse_confidence: str
    core_fields_complete: bool
    response_status_code: int | None = None
    response_final_url: str | None = None
    response_content_length: int = 0
    contains_docked_in_croatia: bool = False
    contains_croatia: bool = False
    croatia_snippet: str | None = None
    docked_snippet: str | None = None
    missing_important_fields: list[str] = field(default_factory=list)
    adapter_candidate_reason: str = ""
    parser_notes: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, object]:
        row = asdict(self)
        row["parser_notes"] = " | ".join(self.parser_notes)
        row["missing_important_fields"] = " | ".join(self.missing_important_fields)
        return row


def main() -> int:
    listing_urls = load_proven_detail_urls(SOURCE_TESTS_PATH)
    for url in REGRESSION_DETAIL_URLS:
        if url not in listing_urls:
            listing_urls.append(url)
    client = PoliteHttpClient()
    listing_page_response = client.get(LISTING_PAGE_URL, max_bytes=350_000)
    listing_page_body = listing_page_response.body or ""
    listing_urls = [
        url for url in listing_urls if url in listing_page_body.replace("\\/", "/") or "marine-one-brokerage" in url
    ][:4]

    parsed_rows: list[MarineOneParsedListing] = []
    for url in listing_urls:
        response = client.get(url, max_bytes=350_000)
        parsed_rows.append(parse_detail_page(url, response))

    parser_status = classify_parser_result(parsed_rows)
    write_outputs(parsed_rows, parser_status)
    print(f"Wrote {JSON_OUTPUT}")
    print(f"Wrote {CSV_OUTPUT}")
    print(f"Parser status: {parser_status}")
    return 0


def load_proven_detail_urls(results_path: Path) -> list[str]:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    for source in payload:
        if source.get("source_id") != "marine_one":
            continue
        urls = [
            page["url"]
            for page in source.get("field_probe_page_results", [])
            if page.get("page_type") == "detail" and page.get("status_code") == 200
        ]
        return urls[:3]
    raise RuntimeError("No proven Marine One detail URLs found in results/source_tests.json")


def parse_detail_page(url: str, response: HttpResponse) -> MarineOneParsedListing:
    html = response.body or ""
    raw_title = extract_meta_content(html, "og:title") or extract_title(html)
    meta_description = extract_meta_description(html)
    jsonld_blocks = extract_jsonld_blocks(html)
    raw_price_text = extract_price_text(meta_description, jsonld_blocks, html)
    currency_hint = extract_currency_hint(meta_description, jsonld_blocks, html)
    product_name = extract_product_name(jsonld_blocks) or derive_name_from_title(raw_title)
    builder_hint, model_hint = split_builder_model(product_name)
    year_hint = extract_year_hint(raw_title, meta_description, html)
    full_text = normalize_response_text(html)
    debug_evidence = build_debug_evidence(response, full_text) if url == ASTREA_42_URL else None
    location_hint, location_evidence_source, location_parser_note = extract_location_hint(meta_description, html, full_text)
    loa_hint = extract_loa_hint(meta_description, html)
    engine_hint, engine_evidence_source, engine_parser_note = extract_engine_hint(html)
    image_present = "og:image" in html.lower() or "<img" in html.lower()
    structured_present = bool(jsonld_blocks) or "schema.org" in html.lower()
    core_fields_complete = all([raw_title, raw_price_text, currency_hint, model_hint, year_hint, loa_hint])
    missing_important_fields = [
        field_name
        for field_name, value in [
            ("location_hint", location_hint),
            ("engine_hint", engine_hint),
        ]
        if value is None
    ]

    notes: list[str] = []
    if location_hint is None:
        notes.append(location_parser_note)
        if debug_evidence:
            notes.append(
                "Astrea 42 debug: "
                f"status={debug_evidence['response_status_code']}, "
                f"final_url={debug_evidence['response_final_url']}, "
                f"content_length={debug_evidence['response_content_length']}, "
                f"contains_croatia={debug_evidence['contains_croatia']}, "
                f"contains_docked_in_croatia={debug_evidence['contains_docked_in_croatia']}"
            )
    if engine_hint is None:
        notes.append(engine_parser_note)
    if raw_price_text is None:
        notes.append("Price was not extracted directly from the sampled raw HTML.")

    return MarineOneParsedListing(
        source_name=SOURCE_NAME,
        listing_url=url,
        raw_title=raw_title,
        raw_price_text=raw_price_text,
        currency_hint=currency_hint,
        builder_hint=builder_hint,
        model_hint=model_hint,
        year_hint=year_hint,
        location_hint=location_hint,
        location_evidence_source=location_evidence_source,
        location_parser_note=location_parser_note,
        loa_hint=loa_hint,
        engine_hint=engine_hint,
        engine_evidence_source=engine_evidence_source,
        engine_parser_note=engine_parser_note,
        image_present=image_present,
        structured_data_present=structured_present,
        price_parse_confidence="high" if raw_price_text and currency_hint else ("medium" if raw_price_text else "low"),
        year_parse_confidence="high" if year_hint else "low",
        model_parse_confidence="high" if builder_hint and model_hint else ("medium" if model_hint else "low"),
        location_parse_confidence="medium_high" if location_evidence_source == "page_text_phrase" else ("medium" if location_hint else "low"),
        loa_parse_confidence="high" if loa_hint else "low",
        response_status_code=debug_evidence["response_status_code"] if debug_evidence else None,
        response_final_url=debug_evidence["response_final_url"] if debug_evidence else None,
        response_content_length=debug_evidence["response_content_length"] if debug_evidence else 0,
        contains_docked_in_croatia=debug_evidence["contains_docked_in_croatia"] if debug_evidence else False,
        contains_croatia=debug_evidence["contains_croatia"] if debug_evidence else False,
        croatia_snippet=debug_evidence["croatia_snippet"] if debug_evidence else None,
        docked_snippet=debug_evidence["docked_snippet"] if debug_evidence else None,
        core_fields_complete=core_fields_complete,
        missing_important_fields=missing_important_fields,
        adapter_candidate_reason=build_adapter_candidate_reason(
            core_fields_complete=core_fields_complete,
            location_hint=location_hint,
            engine_hint=engine_hint,
        ),
        parser_notes=notes,
    )


def classify_parser_result(rows: list[MarineOneParsedListing]) -> str:
    if not rows:
        return "parser_prototype_not_viable"

    strong_rows = [
        row
        for row in rows
        if row.raw_title and row.raw_price_text and row.currency_hint and row.model_hint and row.year_hint and row.loa_hint
    ]
    if len(strong_rows) == len(rows):
        return "parser_prototype_partial" if any(row.location_hint is None or row.engine_hint is None for row in rows) else "parser_prototype_success"
    if strong_rows:
        return "parser_prototype_partial"
    return "parser_prototype_not_viable"


def write_outputs(rows: list[MarineOneParsedListing], parser_status: str) -> None:
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    json_payload = {
        "source_name": SOURCE_NAME,
        "parser_status": parser_status,
        "detail_pages_parsed": len(rows),
        "listings": [asdict(row) for row in rows],
    }
    JSON_OUTPUT.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    fieldnames = [
        "source_name",
        "listing_url",
        "raw_title",
        "raw_price_text",
        "currency_hint",
        "builder_hint",
        "model_hint",
        "year_hint",
        "location_hint",
        "location_evidence_source",
        "location_parser_note",
        "loa_hint",
        "engine_hint",
        "engine_evidence_source",
        "engine_parser_note",
        "image_present",
        "structured_data_present",
        "price_parse_confidence",
        "year_parse_confidence",
        "model_parse_confidence",
        "location_parse_confidence",
        "loa_parse_confidence",
        "response_status_code",
        "response_final_url",
        "response_content_length",
        "contains_docked_in_croatia",
        "contains_croatia",
        "croatia_snippet",
        "docked_snippet",
        "core_fields_complete",
        "missing_important_fields",
        "adapter_candidate_reason",
        "parser_notes",
    ]
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row())


def extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return clean_text(match.group(1))


def extract_meta_content(html: str, property_name: str) -> str | None:
    pattern = re.compile(
        rf'<meta[^>]+property=["\']{re.escape(property_name)}["\'][^>]+content=["\'](.*?)["\']',
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    return clean_text(match.group(1)) if match else None


def extract_meta_description(html: str) -> str | None:
    pattern = re.compile(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    return clean_text(match.group(1)) if match else None


def extract_jsonld_blocks(html: str) -> list[dict]:
    blocks: list[dict] = []
    matches = re.findall(
        r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in matches:
        candidate = raw.strip()
        if not candidate or candidate == "{}":
            continue
        try:
            blocks.append(json.loads(candidate))
        except json.JSONDecodeError:
            continue
    return blocks


def extract_product_name(jsonld_blocks: list[dict]) -> str | None:
    for block in jsonld_blocks:
        if isinstance(block, dict):
            name = block.get("name")
            if isinstance(name, str) and clean_text(name):
                cleaned = clean_text(name)
                if cleaned != "Yachts for sale":
                    return cleaned
    return None


def derive_name_from_title(raw_title: str | None) -> str | None:
    if not raw_title:
        return None
    match = re.search(r"Yachts for sale\s*-\s*(.*?)\s*\|\s*(19|20)\d{2}", raw_title, flags=re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return clean_text(raw_title.replace("Marine One Boat Brokerage", "").replace("Yachts for sale -", ""))


def split_builder_model(name: str | None) -> tuple[str | None, str | None]:
    if not name:
        return None, None
    cleaned = clean_text(name)
    parts = cleaned.split()
    if not parts:
        return None, None
    builder = parts[0]
    model = cleaned
    return builder, model


def extract_price_text(meta_description: str | None, jsonld_blocks: list[dict], html: str) -> str | None:
    if meta_description:
        match = re.search(r"(\u20ac\s*[0-9.,]+)", meta_description)
        if match:
            return clean_price_text(match.group(1))
    for block in jsonld_blocks:
        offers = block.get("offers") if isinstance(block, dict) else None
        if isinstance(offers, dict):
            price = clean_text(str(offers.get("price", "")))
            currency = clean_text(str(offers.get("priceCurrency", "")))
            if price:
                return clean_price_text(f"{currency} {price}".strip())
    match = re.search(r'"price"\s*:\s*"?\s*([0-9][0-9., ]+)\s*"?', html, flags=re.IGNORECASE)
    if match:
        return clean_price_text(match.group(1))
    return None


def extract_currency_hint(meta_description: str | None, jsonld_blocks: list[dict], html: str) -> str | None:
    if meta_description and "\u20ac" in meta_description:
        return "EUR"
    for block in jsonld_blocks:
        offers = block.get("offers") if isinstance(block, dict) else None
        if isinstance(offers, dict) and offers.get("priceCurrency"):
            return clean_text(str(offers["priceCurrency"]))
    match = re.search(r'"priceCurrency"\s*:\s*"([A-Z]{3})"', html, flags=re.IGNORECASE)
    return match.group(1) if match else None


def extract_year_hint(raw_title: str | None, meta_description: str | None, html: str) -> str | None:
    for text in [raw_title or "", meta_description or "", html]:
        match = re.search(r"\b((?:19|20)\d{2})\b", text)
        if match:
            return match.group(1)
    return None


def extract_location_hint(meta_description: str | None, html: str, full_text: str) -> tuple[str | None, str | None, str]:
    phrase_match = find_location_phrase(full_text)
    if phrase_match:
        phrase, location = phrase_match
        if phrase.lower() == "docked in croatia":
            return "Croatia", "page_text_phrase", "Extracted from listing-level phrase: docked in Croatia"
        return location, "page_text_phrase", (
            f'Location was extracted from the listing-level phrase "{phrase}".'
        )

    visible_text = extract_visible_text(html)

    if meta_description:
        match = re.search(r"\b(Croatia|Split|Trogir|Marina|Europe)\b", meta_description, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1)), "meta_description", (
                "Location-like term was found in the public meta description, but it may still be generic."
            )

    labeled_match = re.search(
        r"\b(location|lying|berth|marina)\b[:\s-]{0,10}([A-Z][A-Za-z -]{2,40})\b",
        visible_text,
        flags=re.IGNORECASE,
    )
    if labeled_match:
        candidate = clean_text(labeled_match.group(2))
        if candidate.lower() not in {"document", "href", "sdk", "manager"}:
            return candidate, "page_text_label", (
                "Location hint was found near a location-style label in visible public page text."
            )

    return None, None, "No listing-specific location field was visible in public raw HTML, JSON-LD, or meta text."


def extract_loa_hint(meta_description: str | None, html: str) -> str | None:
    for text in [meta_description or "", html]:
        match = re.search(r"(\d{1,2}[.,]\d\s*m\s*\(\d{1,2}[.,]\d\s*ft\))", text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
        match = re.search(r"(\d{1,2}[.,]\d\s*m)", text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return None


def extract_engine_hint(html: str) -> tuple[str | None, str | None, str]:
    visible_text = extract_visible_text(html)
    label_match = re.search(
        r"\b(engine|engines|motor|power)\b[:\s-]{0,10}([0-9]{2,4}\s*(?:hp|kw)|yanmar|volvo|mercury|honda|diesel)\b",
        visible_text,
        flags=re.IGNORECASE,
    )
    if label_match:
        return clean_text(label_match.group(2)), "page_text_label", (
            "Engine hint was found near an engine-style label in public page text."
        )

    standalone_match = re.search(
        r"\b([0-9]{2,4}\s*(?:hp|kw)|yanmar|volvo|mercury|honda|diesel)\b",
        visible_text,
        flags=re.IGNORECASE,
    )
    if standalone_match:
        return clean_text(standalone_match.group(1)), "page_text_standalone", (
            "Engine-like token was found in public page text, but without a strong label."
        )

    if re.search(r"\bengine(?:s)?\b", visible_text, flags=re.IGNORECASE):
        return None, None, "The word 'engine' was visible, but not as a trustworthy listing-specific field."

    return None, None, "No engine field or trustworthy engine-spec token was visible in public raw HTML, JSON-LD, or meta text."


def build_adapter_candidate_reason(
    *,
    core_fields_complete: bool,
    location_hint: str | None,
    engine_hint: str | None,
) -> str:
    if core_fields_complete and location_hint is None and engine_hint is None:
        return (
            "Core identity, pricing, year, and LOA fields parse reliably from a tiny public sample; "
            "location and engine remain missing, so this is a strong but partial adapter candidate."
        )
    if core_fields_complete:
        return "Core parser fields are complete on the tiny public sample, making this a practical adapter candidate."
    return "Important core fields are still incomplete, so adapter work should wait."


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().strip('"')


def clean_price_text(value: str) -> str:
    return clean_text(value).rstrip(".")


def extract_visible_text(html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text(text)


def find_location_phrase(visible_text: str) -> tuple[str, str] | None:
    patterns = [
        r"(docked in\s+(Croatia))",
        r"(moored in\s+(Croatia))",
        r"(currently docked in\s+(Croatia))",
        r"(lying in\s+(Croatia))",
        r"(located in\s+(Croatia))",
        r"(berthed in\s+(Croatia))",
    ]
    for pattern in patterns:
        match = re.search(pattern, visible_text, flags=re.IGNORECASE)
        if match:
            phrase = clean_text(match.group(1))
            location = clean_text(match.group(2))
            return phrase, location
    return None


def normalize_response_text(raw_html: str) -> str:
    return clean_text(html.unescape(raw_html)).lower()


def build_debug_evidence(response: HttpResponse, full_text: str) -> dict[str, object]:
    croatia_index = full_text.find("croatia")
    docked_index = full_text.find("docked")
    return {
        "response_status_code": response.status_code,
        "response_final_url": response.final_url,
        "response_content_length": len(response.body or ""),
        "contains_docked_in_croatia": "docked in croatia" in full_text,
        "contains_croatia": "croatia" in full_text,
        "croatia_snippet": snippet_around(full_text, croatia_index) if croatia_index >= 0 else None,
        "docked_snippet": snippet_around(full_text, docked_index) if docked_index >= 0 else None,
    }


def snippet_around(text: str, index: int, radius: int = 150) -> str:
    if index < 0:
        return ""
    start = max(0, index - radius)
    end = min(len(text), index + radius)
    return text[start:end]
