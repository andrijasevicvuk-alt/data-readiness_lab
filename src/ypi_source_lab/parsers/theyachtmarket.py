from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..http_client import HttpResponse, PoliteHttpClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DETAIL_DISCOVERY_PATH = PROJECT_ROOT / "results" / "detail_discovery_results.json"
JSON_OUTPUT = PROJECT_ROOT / "results" / "theyachtmarket_parser_sample.json"
CSV_OUTPUT = PROJECT_ROOT / "results" / "theyachtmarket_parser_sample.csv"
SOURCE_NAME = "TheYachtMarket"
SOURCE_ID = "theyachtmarket"


@dataclass
class TheYachtMarketParsedListing:
    source_name: str
    listing_url: str
    raw_title: str | None
    raw_price_text: str | None
    currency_hint: str | None
    builder_hint: str | None
    model_hint: str | None
    year_hint: str | None
    location_hint: str | None
    loa_hint: str | None
    engine_hint: str | None
    fuel_hint: str | None
    boat_type_hint: str | None
    broker_hint: str | None
    image_present: bool
    structured_data_present: bool
    price_parse_confidence: str
    year_parse_confidence: str
    model_parse_confidence: str
    location_parse_confidence: str
    loa_parse_confidence: str
    engine_parse_confidence: str
    parser_notes: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, object]:
        row = asdict(self)
        row["parser_notes"] = " | ".join(self.parser_notes)
        return row


def main() -> int:
    listing_urls = load_proven_detail_urls(DETAIL_DISCOVERY_PATH)
    client = PoliteHttpClient()
    parsed_rows: list[TheYachtMarketParsedListing] = []
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
    urls = [
        item["candidate_detail_url"]
        for item in payload
        if item.get("source_id") == SOURCE_ID and item.get("is_probable_detail_page") is True
    ]
    if len(urls) < 3:
        raise RuntimeError("Expected 3 proven TheYachtMarket detail URLs in results/detail_discovery_results.json")
    return urls[:3]


def parse_detail_page(url: str, response: HttpResponse) -> TheYachtMarketParsedListing:
    raw_html = response.body or ""
    visible_text = extract_visible_text(raw_html)
    raw_title = extract_title(raw_html)
    meta_description = extract_meta_description(raw_html)
    jsonld_blocks = extract_jsonld_blocks(raw_html)
    headline = extract_headline(raw_title)

    raw_price_text = extract_price_text(visible_text, meta_description, jsonld_blocks)
    currency_hint = extract_currency_hint(raw_price_text, meta_description, jsonld_blocks, visible_text)
    builder_hint, model_hint = split_builder_model(headline)
    year_hint = extract_year_hint(raw_title, meta_description, visible_text)
    location_hint = extract_location_hint(raw_title, visible_text)
    loa_hint = extract_loa_hint(visible_text)
    engine_hint = extract_engine_hint(visible_text)
    fuel_hint = extract_fuel_hint(visible_text)
    boat_type_hint = extract_boat_type_hint(visible_text)
    broker_hint = extract_broker_hint(visible_text, jsonld_blocks)
    image_present = "og:image" in raw_html.lower() or "<img" in raw_html.lower()
    structured_data_present = bool(jsonld_blocks) or "application/ld+json" in raw_html.lower()

    notes: list[str] = []
    if broker_hint is None:
        notes.append("Broker field was not clearly visible in the sampled public raw HTML.")
    if engine_hint is None:
        notes.append("Engine field was not confidently parsed from the sampled public raw HTML.")
    if fuel_hint is None:
        notes.append("Fuel field was not clearly visible in the sampled public raw HTML.")

    return TheYachtMarketParsedListing(
        source_name=SOURCE_NAME,
        listing_url=url,
        raw_title=raw_title,
        raw_price_text=raw_price_text,
        currency_hint=currency_hint,
        builder_hint=builder_hint,
        model_hint=model_hint,
        year_hint=year_hint,
        location_hint=location_hint,
        loa_hint=loa_hint,
        engine_hint=engine_hint,
        fuel_hint=fuel_hint,
        boat_type_hint=boat_type_hint,
        broker_hint=broker_hint,
        image_present=image_present,
        structured_data_present=structured_data_present,
        price_parse_confidence="high" if raw_price_text and currency_hint else ("medium" if raw_price_text else "low"),
        year_parse_confidence="high" if year_hint else "low",
        model_parse_confidence="high" if builder_hint and model_hint else ("medium" if model_hint else "low"),
        location_parse_confidence="high" if location_hint else "low",
        loa_parse_confidence="high" if loa_hint else "low",
        engine_parse_confidence="high" if engine_hint else "low",
        parser_notes=notes,
    )


def classify_parser_result(rows: list[TheYachtMarketParsedListing]) -> str:
    if not rows:
        return "parser_prototype_not_viable"

    strong_rows = [
        row
        for row in rows
        if row.raw_title
        and row.raw_price_text
        and row.currency_hint
        and row.model_hint
        and row.year_hint
        and row.location_hint
        and row.loa_hint
    ]
    if len(strong_rows) != len(rows):
        return "parser_prototype_partial" if strong_rows else "parser_prototype_not_viable"

    if any(row.engine_hint is None or row.fuel_hint is None for row in rows):
        return "parser_prototype_partial"
    return "parser_prototype_success"


def write_outputs(rows: list[TheYachtMarketParsedListing], parser_status: str) -> None:
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
        "loa_hint",
        "engine_hint",
        "fuel_hint",
        "boat_type_hint",
        "broker_hint",
        "image_present",
        "structured_data_present",
        "price_parse_confidence",
        "year_parse_confidence",
        "model_parse_confidence",
        "location_parse_confidence",
        "loa_parse_confidence",
        "engine_parse_confidence",
        "parser_notes",
    ]
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row())


def extract_title(raw_html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    return clean_text(match.group(1)) if match else None


def extract_meta_description(raw_html: str) -> str | None:
    pattern = re.compile(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(raw_html)
    return clean_text(match.group(1)) if match else None


def extract_jsonld_blocks(raw_html: str) -> list[dict]:
    blocks: list[dict] = []
    matches = re.findall(
        r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in matches:
        candidate = raw.strip()
        if not candidate or candidate == "{}":
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            blocks.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            blocks.append(parsed)
    return blocks


def extract_headline(raw_title: str | None) -> str | None:
    if not raw_title:
        return None
    headline = raw_title.split(" for Sale in ")[0]
    headline = headline.replace(" Used Boat for", "")
    headline = headline.replace(" for Sale", "")
    return clean_text(headline)


def split_builder_model(headline: str | None) -> tuple[str | None, str | None]:
    if not headline:
        return None, None

    multiword_builders = ["Rafnar Maritime"]
    for builder in multiword_builders:
        if headline.startswith(builder + " "):
            return builder, clean_text(headline[len(builder) :])

    parts = headline.split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], clean_text(" ".join(parts[1:]))


def extract_price_text(visible_text: str, meta_description: str | None, jsonld_blocks: list[dict]) -> str | None:
    header_match = re.search(
        r"for sale \((?:19|20)\d{2}\) in .*?([£€$][0-9,.\s]+\s*(?:GBP|EUR|USD))(?:\s+(Listed price\s+[€£$][0-9,.\s]+\s*(?:EUR|GBP|USD)))?",
        visible_text,
        flags=re.IGNORECASE,
    )
    if header_match:
        primary_price = clean_text(header_match.group(1))
        listed_price = clean_text(header_match.group(2)) if header_match.group(2) else None
        return clean_text(f"{primary_price} {listed_price}".strip()) if listed_price else primary_price

    listed_match = re.search(
        r"(Listed price\s+[€£$][0-9,.\s]+\s*(?:EUR|GBP|USD))",
        visible_text,
        flags=re.IGNORECASE,
    )
    if listed_match:
        return clean_text(listed_match.group(1))

    sale_match = re.search(r"([€£$][0-9,.\s]+\s*(?:EUR|GBP|USD))", visible_text, flags=re.IGNORECASE)
    if sale_match:
        return clean_text(sale_match.group(1))

    if meta_description:
        meta_match = re.search(r"(Priced at\s+[€£$]?[0-9,.\s]+\s*(?:EUR|GBP|USD))", meta_description, flags=re.IGNORECASE)
        if meta_match:
            return clean_text(meta_match.group(1))

    for block in jsonld_blocks:
        offers = block.get("offers") if isinstance(block, dict) else None
        if isinstance(offers, dict):
            price = clean_text(str(offers.get("price", "")))
            currency = clean_text(str(offers.get("priceCurrency", "")))
            if price:
                return clean_text(f"{price} {currency}".strip())
    return None


def extract_currency_hint(
    raw_price_text: str | None,
    meta_description: str | None,
    jsonld_blocks: list[dict],
    visible_text: str,
) -> str | None:
    for text in [raw_price_text or "", meta_description or "", visible_text]:
        if "EUR" in text or "€" in text:
            return "EUR"
        if "GBP" in text or "£" in text:
            return "GBP"
        if "USD" in text or "$" in text:
            return "USD"

    for block in jsonld_blocks:
        offers = block.get("offers") if isinstance(block, dict) else None
        if isinstance(offers, dict):
            currency = offers.get("priceCurrency")
            if isinstance(currency, str) and currency.strip():
                return clean_text(currency)
    return None


def extract_year_hint(raw_title: str | None, meta_description: str | None, visible_text: str) -> str | None:
    for text in [raw_title or "", meta_description or "", visible_text]:
        match = re.search(r"\b((?:19|20)\d{2})\b", text)
        if match:
            return match.group(1)
    return None


def extract_location_hint(raw_title: str | None, visible_text: str) -> str | None:
    if raw_title:
        match = re.search(r"for Sale in (.*?) - (?:19|20)\d{2}", raw_title, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))

    match = re.search(r"\bLocation\s+([A-Z][A-Za-z, -]{2,60})", visible_text)
    if match:
        return clean_text(match.group(1))
    return None


def extract_loa_hint(visible_text: str) -> str | None:
    match = re.search(r"Length overall\s+([0-9]+(?:\.[0-9]+)?)", visible_text, flags=re.IGNORECASE)
    if match:
        return clean_text(f"{match.group(1)} m")

    match = re.search(r"overall length of\s+([0-9]+(?:\.[0-9]+)?)\s+metres", visible_text, flags=re.IGNORECASE)
    if match:
        return clean_text(f"{match.group(1)} m")
    return None


def extract_engine_hint(visible_text: str) -> str | None:
    match = re.search(
        r"Engine\s+([^.]{0,80}?)(?=\s+Fuel\b|\s+Accommodation\b|\s+This\b)",
        visible_text,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = clean_text(match.group(1))
        if is_trustworthy_engine_text(candidate):
            return candidate

    match = re.search(
        r"(dual\s+[A-Z][A-Za-z0-9 ]+\s+[0-9]{2,4}\s*HP\s+engines?)",
        visible_text,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = clean_text(match.group(1))
        if is_trustworthy_engine_text(candidate):
            return candidate

    match = re.search(
        r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z0-9][A-Za-z0-9-]+){0,4}\s+marine diesel engine)",
        visible_text,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = clean_text(match.group(1))
        if is_trustworthy_engine_text(candidate):
            return candidate

    match = re.search(r"(powered by\s+[0-9]{2,4}\s+bhp)", visible_text, flags=re.IGNORECASE)
    if match:
        candidate = clean_text(match.group(1))
        if is_trustworthy_engine_text(candidate):
            return candidate
    return None


def extract_fuel_hint(visible_text: str) -> str | None:
    match = re.search(
        r"Fuel\s+(Diesel|Petrol/Gasoline|Petrol|Gasoline|Electric|Hybrid)",
        visible_text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(1))
    return None


def extract_boat_type_hint(visible_text: str) -> str | None:
    patterns = [
        r"\b(sailing yacht)\b",
        r"\b(motor yacht)\b",
        r"\b(cross cabin)\b",
        r"\b(yacht)\b",
        r"\b(boat)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, visible_text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    return None


def extract_broker_hint(visible_text: str, jsonld_blocks: list[dict]) -> str | None:
    for block in jsonld_blocks:
        seller = block.get("seller") if isinstance(block, dict) else None
        if isinstance(seller, dict):
            name = seller.get("name")
            if isinstance(name, str) and name.strip():
                return clean_text(name)

    match = re.search(r"Sold by\s+([A-Z][A-Za-z0-9&'., -]{2,80})", visible_text)
    if match:
        return clean_text(match.group(1))
    return None


def is_trustworthy_engine_text(value: str) -> bool:
    lowered = value.lower()
    if "disclaimer" in lowered or "contact" in lowered:
        return False
    return any(
        token in lowered
        for token in [
            "hp",
            "bhp",
            "volvo",
            "penta",
            "man",
            "mercury",
            "yanmar",
            "diesel",
            "v12",
        ]
    )


def extract_visible_text(raw_html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text(html.unescape(text))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().strip('"')
