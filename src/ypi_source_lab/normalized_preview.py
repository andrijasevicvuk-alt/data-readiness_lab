from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"

RAW_DATASET_INPUT = RESULTS_DIR / "market_dataset_pilot_raw.json"
DUPLICATES_INPUT = RESULTS_DIR / "duplicate_candidates.json"

JSON_OUTPUT = RESULTS_DIR / "normalized_dataset_preview.json"
CSV_OUTPUT = RESULTS_DIR / "normalized_dataset_preview.csv"


@dataclass
class NormalizedPreviewRecord:
    source_name: str
    listing_url: str
    canonical_builder_draft: str | None
    canonical_model_draft: str | None
    year_built_draft: int | None
    price_amount_draft: float | None
    currency_draft: str | None
    price_eur_draft: float | None
    country_draft: str | None
    location_text_draft: str | None
    loa_m_draft: float | None
    engine_signature_draft: str | None
    boat_type_draft: str | None
    duplicate_cluster_id_suggestion: str
    duplicate_confidence: str
    data_quality_score: int
    valuation_ready_candidate: bool
    exclusion_reason: str | None
    review_required: bool
    review_reason: str | None


def main() -> int:
    payload = build_normalized_preview_payload()
    write_outputs(payload)
    print(f"Wrote {JSON_OUTPUT}")
    print(f"Wrote {CSV_OUTPUT}")
    return 0


def build_normalized_preview_payload() -> dict[str, object]:
    raw_payload = json.loads(RAW_DATASET_INPUT.read_text(encoding="utf-8"))
    duplicate_candidates = json.loads(DUPLICATES_INPUT.read_text(encoding="utf-8"))
    raw_records = raw_payload.get("records", [])

    duplicate_lookup, cluster_members = build_duplicate_lookup(duplicate_candidates)

    normalized_records: list[NormalizedPreviewRecord] = []
    for record in raw_records:
        normalized = normalize_record(record, duplicate_lookup)
        normalized_records.append(normalized)

    excluded = [record for record in normalized_records if not record.valuation_ready_candidate]
    ready = [record for record in normalized_records if record.valuation_ready_candidate]

    cluster_summary = []
    for cluster_id, members in sorted(cluster_members.items()):
        best_confidence = max(
            (duplicate_lookup.get(url, {}).get("duplicate_confidence", "none") for url in members),
            key=duplicate_confidence_rank,
            default="none",
        )
        cluster_summary.append(
            {
                "cluster_id": cluster_id,
                "member_count": len(members),
                "member_urls": sorted(members),
                "highest_duplicate_confidence": best_confidence,
            }
        )

    return {
        "raw_record_count": len(raw_records),
        "normalized_record_count": len(normalized_records),
        "valuation_ready_candidate_count": len(ready),
        "excluded_record_count": len(excluded),
        "duplicate_cluster_count": len(cluster_summary),
        "duplicate_clusters": cluster_summary,
        "records": [asdict(record) for record in normalized_records],
    }


def normalize_record(record: dict, duplicate_lookup: dict[str, dict[str, object]]) -> NormalizedPreviewRecord:
    listing_url = record["listing_url"]
    duplicate_info = duplicate_lookup.get(listing_url, {})

    canonical_builder, canonical_model = normalize_builder_and_model(
        record.get("builder_hint"),
        record.get("model_hint"),
    )
    year_built = parse_year(record.get("year_hint"))
    price_amount, currency = parse_price_amount_and_currency(
        record.get("raw_price_text"),
        record.get("currency_hint"),
    )
    location_text = clean_text(record.get("location_hint"))
    country = extract_country(location_text)
    loa_m = parse_loa_m(record.get("loa_hint"))
    engine_signature = clean_text(record.get("engine_hint"))
    boat_type = normalize_boat_type(record.get("boat_type_hint"))

    duplicate_confidence = str(duplicate_info.get("duplicate_confidence", "none"))
    duplicate_cluster_id = str(
        duplicate_info.get("duplicate_cluster_id_suggestion", build_unique_cluster_id(record))
    )

    price_eur = price_amount if currency == "EUR" else None
    data_quality_score = calculate_data_quality_score(
        record=record,
        canonical_builder=canonical_builder,
        canonical_model=canonical_model,
        year_built=year_built,
        price_amount=price_amount,
        currency=currency,
        country=country,
        loa_m=loa_m,
        engine_signature=engine_signature,
        duplicate_confidence=duplicate_confidence,
    )

    exclusion_reasons: list[str] = []
    review_reasons: list[str] = []

    if price_amount is None:
        exclusion_reasons.append("price amount missing")
    if currency is None:
        exclusion_reasons.append("currency missing")
    if canonical_builder is None or canonical_model is None:
        exclusion_reasons.append("builder/model draft incomplete")
    if year_built is None:
        exclusion_reasons.append("year missing")
    if country is None:
        exclusion_reasons.append("country/location missing")
    if loa_m is None:
        exclusion_reasons.append("LOA missing")
    if duplicate_confidence in {"high", "medium"}:
        exclusion_reasons.append(f"duplicate review required ({duplicate_confidence})")
    if data_quality_score < 70:
        exclusion_reasons.append("data quality score below valuation threshold")

    if price_eur is None and currency is not None:
        review_reasons.append(f"price remains in {currency} (EUR conversion deferred to main YPI)")
    if engine_signature is None:
        review_reasons.append("engine signature missing or weak")
    if record.get("parser_status") == "parser_prototype_partial":
        review_reasons.append("source parser remains partial in the source lab")
    if duplicate_confidence == "low":
        review_reasons.append("low-confidence duplicate watchlist match")

    valuation_ready_candidate = len(exclusion_reasons) == 0
    review_required = bool(review_reasons or exclusion_reasons)

    return NormalizedPreviewRecord(
        source_name=record["source_name"],
        listing_url=listing_url,
        canonical_builder_draft=canonical_builder,
        canonical_model_draft=canonical_model,
        year_built_draft=year_built,
        price_amount_draft=price_amount,
        currency_draft=currency,
        price_eur_draft=price_eur,
        country_draft=country,
        location_text_draft=location_text,
        loa_m_draft=loa_m,
        engine_signature_draft=engine_signature,
        boat_type_draft=boat_type,
        duplicate_cluster_id_suggestion=duplicate_cluster_id,
        duplicate_confidence=duplicate_confidence,
        data_quality_score=data_quality_score,
        valuation_ready_candidate=valuation_ready_candidate,
        exclusion_reason="; ".join(exclusion_reasons) if exclusion_reasons else None,
        review_required=review_required,
        review_reason="; ".join(review_reasons) if review_reasons else None,
    )


def build_duplicate_lookup(candidates: list[dict]) -> tuple[dict[str, dict[str, object]], dict[str, set[str]]]:
    lookup: dict[str, dict[str, object]] = {}
    clusters: dict[str, set[str]] = {}
    for candidate in candidates:
        cluster_id = candidate["suggested_cluster_id"]
        clusters.setdefault(cluster_id, set()).update(
            [candidate["record_a_url"], candidate["record_b_url"]]
        )
        for url in [candidate["record_a_url"], candidate["record_b_url"]]:
            current = lookup.get(url)
            if current is None or float(candidate["duplicate_score"]) > float(current["duplicate_score"]):
                lookup[url] = {
                    "duplicate_cluster_id_suggestion": cluster_id,
                    "duplicate_confidence": candidate["duplicate_confidence"],
                    "duplicate_score": float(candidate["duplicate_score"]),
                    "duplicate_reason": candidate["duplicate_reason"],
                }
    return lookup, clusters


def normalize_builder_and_model(builder_hint: str | None, model_hint: str | None) -> tuple[str | None, str | None]:
    builder = clean_text(builder_hint)
    model = clean_text(model_hint)

    if not builder and not model:
        return None, None

    known_builders = [
        "Fountaine Pajot",
        "Rafnar Maritime",
        "Beneteau",
        "Riva",
        "Bali",
    ]
    if model:
        for candidate in known_builders:
            if model.lower().startswith(candidate.lower()):
                builder = candidate
                suffix = model[len(candidate) :].strip(" -")
                model = suffix or model
                break

    if builder and model and model.lower().startswith(builder.lower()):
        suffix = model[len(builder) :].strip(" -")
        if suffix:
            model = suffix

    return builder, model


def parse_price_amount_and_currency(raw_price_text: str | None, currency_hint: str | None) -> tuple[float | None, str | None]:
    if not raw_price_text:
        return None, currency_hint

    currency = currency_hint or infer_currency(raw_price_text)
    if currency is None:
        return None, None

    symbol_map = {"EUR": "€", "GBP": "£", "USD": "$"}
    symbol = symbol_map.get(currency, "")
    patterns = [
        rf"{re.escape(symbol)}\s*([0-9][0-9.,\s]*)" if symbol else None,
        rf"([0-9][0-9.,\s]*)\s*{currency}",
    ]

    for pattern in patterns:
        if not pattern:
            continue
        match = re.search(pattern, raw_price_text, flags=re.IGNORECASE)
        if not match:
            continue
        amount = parse_decimal_number(match.group(1))
        if amount is not None:
            return amount, currency

    generic_match = re.search(r"([0-9][0-9.,\s]*)", raw_price_text)
    if generic_match:
        return parse_decimal_number(generic_match.group(1)), currency
    return None, currency


def infer_currency(raw_price_text: str) -> str | None:
    upper = raw_price_text.upper()
    if "EUR" in upper or "€" in raw_price_text:
        return "EUR"
    if "GBP" in upper or "£" in raw_price_text:
        return "GBP"
    if "USD" in upper or "$" in raw_price_text:
        return "USD"
    return None


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b((?:19|20)\d{2})\b", value)
    return int(match.group(1)) if match else None


def parse_loa_m(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]{1,2}(?:[.,][0-9]{1,2})?)\s*m", value.lower())
    if not match:
        match = re.search(r"([0-9]{1,2}(?:[.,][0-9]{1,2})?)", value.lower())
    if not match:
        return None
    return parse_decimal_number(match.group(1))


def parse_decimal_number(value: str) -> float | None:
    compact = re.sub(r"\s+", "", value)
    if not compact:
        return None

    if "," in compact and "." in compact:
        if compact.rfind(",") > compact.rfind("."):
            compact = compact.replace(".", "").replace(",", ".")
        else:
            compact = compact.replace(",", "")
    elif "," in compact:
        parts = compact.split(",")
        if len(parts[-1]) in {1, 2}:
            compact = compact.replace(",", ".")
        else:
            compact = compact.replace(",", "")
    else:
        compact = compact

    try:
        return float(compact)
    except ValueError:
        return None


def extract_country(location_text: str | None) -> str | None:
    if not location_text:
        return None
    if "," in location_text:
        return location_text.split(",")[-1].strip()
    return location_text.strip()


def normalize_boat_type(value: str | None) -> str | None:
    text = clean_text(value)
    return text.lower() if text else None


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", value).strip()


def calculate_data_quality_score(
    *,
    record: dict,
    canonical_builder: str | None,
    canonical_model: str | None,
    year_built: int | None,
    price_amount: float | None,
    currency: str | None,
    country: str | None,
    loa_m: float | None,
    engine_signature: str | None,
    duplicate_confidence: str,
) -> int:
    score = 0
    if price_amount is not None:
        score += 15
    if currency is not None:
        score += 10
    if canonical_builder and canonical_model:
        score += 20
    if year_built is not None:
        score += 10
    if country is not None:
        score += 10
    if loa_m is not None:
        score += 10
    if engine_signature is not None:
        score += 5

    score += source_reliability_points(record.get("source_role"))
    score += parser_confidence_points(record.get("parser_status"))
    score += duplicate_risk_points(duplicate_confidence)
    return min(score, 100)


def source_reliability_points(source_role: str | None) -> int:
    if source_role == "broader_marketplace_backbone":
        return 10
    if source_role == "local_broker_trust_anchor":
        return 8
    return 5


def parser_confidence_points(parser_status: str | None) -> int:
    if parser_status == "parser_prototype_success":
        return 10
    if parser_status == "parser_prototype_partial":
        return 7
    return 4


def duplicate_risk_points(duplicate_confidence: str) -> int:
    if duplicate_confidence == "none":
        return 10
    if duplicate_confidence == "low":
        return 6
    if duplicate_confidence == "medium":
        return 3
    return 0


def duplicate_confidence_rank(value: str) -> int:
    order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    return order.get(value, 0)


def build_unique_cluster_id(record: dict) -> str:
    raw = f"{record.get('source_name','unknown')}|{record.get('listing_url','')}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"unique-{digest}"


def write_outputs(payload: dict[str, object]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    records = payload.get("records", [])
    fieldnames = list(NormalizedPreviewRecord.__dataclass_fields__.keys())
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
