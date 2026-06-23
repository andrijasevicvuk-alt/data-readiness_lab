from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .duplicate_candidates import build_duplicate_candidates, write_duplicate_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"

MARINE_ONE_INPUT = RESULTS_DIR / "marine_one_parser_sample.json"
THEYACHTMARKET_INPUT = RESULTS_DIR / "theyachtmarket_parser_sample.json"

RAW_JSON_OUTPUT = RESULTS_DIR / "market_dataset_pilot_raw.json"
RAW_CSV_OUTPUT = RESULTS_DIR / "market_dataset_pilot_raw.csv"


@dataclass
class MarketPilotRecord:
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
    image_present: bool
    parser_status: str
    source_role: str
    data_quality_notes: str


def main() -> int:
    records = build_market_dataset_pilot()
    write_market_dataset_outputs(records)
    duplicate_candidates = build_duplicate_candidates([asdict(record) for record in records])
    write_duplicate_outputs(duplicate_candidates)
    print(f"Wrote {RAW_JSON_OUTPUT}")
    print(f"Wrote {RAW_CSV_OUTPUT}")
    print(f"Wrote {RESULTS_DIR / 'duplicate_candidates.json'}")
    print(f"Wrote {RESULTS_DIR / 'duplicate_candidates.csv'}")
    return 0


def build_market_dataset_pilot() -> list[MarketPilotRecord]:
    records: list[MarketPilotRecord] = []
    for payload_path in [THEYACHTMARKET_INPUT, MARINE_ONE_INPUT]:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        parser_status = payload.get("parser_status", "unknown")
        source_name = payload.get("source_name", "unknown")
        source_role = infer_source_role(source_name)
        for listing in payload.get("listings", []):
            records.append(
                MarketPilotRecord(
                    source_name=source_name,
                    listing_url=listing.get("listing_url"),
                    raw_title=listing.get("raw_title"),
                    raw_price_text=listing.get("raw_price_text"),
                    currency_hint=listing.get("currency_hint"),
                    builder_hint=listing.get("builder_hint"),
                    model_hint=listing.get("model_hint"),
                    year_hint=listing.get("year_hint"),
                    location_hint=listing.get("location_hint"),
                    loa_hint=listing.get("loa_hint"),
                    engine_hint=listing.get("engine_hint"),
                    fuel_hint=listing.get("fuel_hint"),
                    boat_type_hint=listing.get("boat_type_hint"),
                    image_present=bool(listing.get("image_present")),
                    parser_status=parser_status,
                    source_role=source_role,
                    data_quality_notes=build_quality_notes(listing, parser_status, source_role),
                )
            )
    return records


def infer_source_role(source_name: str) -> str:
    if source_name == "TheYachtMarket":
        return "broader_marketplace_backbone"
    if source_name == "Marine One / YachtBrokerage":
        return "local_broker_trust_anchor"
    return "not_ready"


def build_quality_notes(listing: dict, parser_status: str, source_role: str) -> str:
    notes: list[str] = [f"parser_status={parser_status}", f"source_role={source_role}"]
    if listing.get("parser_notes"):
        if isinstance(listing["parser_notes"], list):
            notes.extend(listing["parser_notes"])
        else:
            notes.append(str(listing["parser_notes"]))
    if listing.get("missing_important_fields"):
        missing = listing["missing_important_fields"]
        if isinstance(missing, list) and missing:
            notes.append("missing_fields=" + ", ".join(missing))
    if listing.get("location_hint") is None:
        notes.append("location remains weak or absent in this sample.")
    if listing.get("engine_hint") is None:
        notes.append("engine remains weak or absent in this sample.")
    return " | ".join(notes)


def write_market_dataset_outputs(records: list[MarketPilotRecord]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_payload = {
        "record_count": len(records),
        "records": [asdict(record) for record in records],
    }
    RAW_JSON_OUTPUT.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")

    with RAW_CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
                "image_present",
                "parser_status",
                "source_role",
                "data_quality_notes",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
