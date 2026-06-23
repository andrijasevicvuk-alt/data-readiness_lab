from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
DUPLICATE_JSON_OUTPUT = RESULTS_DIR / "duplicate_candidates.json"
DUPLICATE_CSV_OUTPUT = RESULTS_DIR / "duplicate_candidates.csv"


@dataclass
class DuplicateCandidate:
    record_a_url: str
    record_b_url: str
    duplicate_score: float
    duplicate_confidence: str
    duplicate_reason: str
    suggested_cluster_id: str
    review_required: bool

    def to_row(self) -> dict[str, object]:
        row = asdict(self)
        row["duplicate_score"] = f"{self.duplicate_score:.3f}"
        return row


def build_duplicate_candidates(records: list[dict]) -> list[DuplicateCandidate]:
    candidates: list[DuplicateCandidate] = []
    for index, record_a in enumerate(records):
        for record_b in records[index + 1 :]:
            candidate = compare_records(record_a, record_b)
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(key=lambda item: item.duplicate_score, reverse=True)
    return candidates


def compare_records(record_a: dict, record_b: dict) -> DuplicateCandidate | None:
    title_similarity = similarity(normalize_title(record_a.get("raw_title")), normalize_title(record_b.get("raw_title")))
    builder_model_similarity = similarity(
        normalize_simple_text(f"{record_a.get('builder_hint', '')} {record_a.get('model_hint', '')}"),
        normalize_simple_text(f"{record_b.get('builder_hint', '')} {record_b.get('model_hint', '')}"),
    )

    year_a = parse_year(record_a.get("year_hint"))
    year_b = parse_year(record_b.get("year_hint"))
    loa_a = parse_loa(record_a.get("loa_hint"))
    loa_b = parse_loa(record_b.get("loa_hint"))
    price_a = parse_price(record_a.get("raw_price_text"), record_a.get("currency_hint"))
    price_b = parse_price(record_b.get("raw_price_text"), record_b.get("currency_hint"))
    location_similarity = similarity(
        normalize_simple_text(record_a.get("location_hint")),
        normalize_simple_text(record_b.get("location_hint")),
    )
    engine_similarity = similarity(
        normalize_simple_text(record_a.get("engine_hint")),
        normalize_simple_text(record_b.get("engine_hint")),
    )

    score = 0.0
    reasons: list[str] = []

    if title_similarity >= 0.92:
        score += 0.32
        reasons.append(f"title similarity {title_similarity:.2f}")
    elif title_similarity >= 0.82:
        score += 0.22
        reasons.append(f"title similarity {title_similarity:.2f}")

    if builder_model_similarity >= 0.94:
        score += 0.26
        reasons.append(f"builder/model similarity {builder_model_similarity:.2f}")
    elif builder_model_similarity >= 0.84:
        score += 0.18
        reasons.append(f"builder/model similarity {builder_model_similarity:.2f}")

    if year_a is not None and year_b is not None:
        year_diff = abs(year_a - year_b)
        if year_diff == 0:
            score += 0.10
            reasons.append("same year")
        elif year_diff == 1:
            score += 0.05
            reasons.append("close year")

    if loa_a is not None and loa_b is not None:
        loa_diff = abs(loa_a - loa_b)
        if loa_diff <= 0.35:
            score += 0.10
            reasons.append(f"very close LOA ({loa_diff:.2f}m)")
        elif loa_diff <= 0.75:
            score += 0.05
            reasons.append(f"close LOA ({loa_diff:.2f}m)")

    if price_a is not None and price_b is not None:
        same_currency = price_a["currency"] == price_b["currency"]
        if same_currency:
            price_diff_ratio = abs(price_a["amount"] - price_b["amount"]) / max(price_a["amount"], price_b["amount"])
            if price_diff_ratio <= 0.05:
                score += 0.13
                reasons.append(f"very close price ({price_diff_ratio:.1%})")
            elif price_diff_ratio <= 0.12:
                score += 0.07
                reasons.append(f"close price ({price_diff_ratio:.1%})")
        else:
            reasons.append("price currency differs")

    if location_similarity >= 0.92:
        score += 0.06
        reasons.append("same or nearly same location")
    elif location_similarity >= 0.75:
        score += 0.03
        reasons.append("related location")

    if engine_similarity >= 0.88:
        score += 0.03
        reasons.append("similar engine text")
    elif engine_similarity >= 0.72:
        score += 0.015
        reasons.append("related engine text")

    if record_a.get("image_present") and record_b.get("image_present"):
        score += 0.01
        reasons.append("both listings have images")

    if score < 0.55:
        return None

    confidence = "high" if score >= 0.80 else ("medium" if score >= 0.65 else "low")
    cluster_id = build_cluster_id(record_a, record_b)
    return DuplicateCandidate(
        record_a_url=record_a["listing_url"],
        record_b_url=record_b["listing_url"],
        duplicate_score=round(score, 3),
        duplicate_confidence=confidence,
        duplicate_reason="; ".join(reasons),
        suggested_cluster_id=cluster_id,
        review_required=True,
    )


def write_duplicate_outputs(candidates: list[DuplicateCandidate]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DUPLICATE_JSON_OUTPUT.write_text(
        json.dumps([asdict(item) for item in candidates], indent=2),
        encoding="utf-8",
    )
    with DUPLICATE_CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "record_a_url",
                "record_b_url",
                "duplicate_score",
                "duplicate_confidence",
                "duplicate_reason",
                "suggested_cluster_id",
                "review_required",
            ],
        )
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(candidate.to_row())


def normalize_title(value: str | None) -> str:
    normalized = normalize_simple_text(value)
    stopwords = {
        "yachts",
        "yacht",
        "used",
        "boat",
        "sale",
        "for",
        "in",
        "marine",
        "one",
        "brokerage",
    }
    parts = [token for token in normalized.split() if token not in stopwords]
    return " ".join(parts)


def normalize_simple_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower()
    lowered = lowered.replace("€", " eur ").replace("£", " gbp ").replace("$", " usd ")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(a=left, b=right).ratio()


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b((?:19|20)\d{2})\b", value)
    return int(match.group(1)) if match else None


def parse_loa(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]{1,2}(?:[.,][0-9]{1,2})?)\s*m", value.lower())
    if not match:
        match = re.search(r"([0-9]{1,2}(?:[.,][0-9]{1,2})?)", value.lower())
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def parse_price(raw_price_text: str | None, currency_hint: str | None) -> dict[str, object] | None:
    if not raw_price_text:
        return None
    currency = currency_hint or infer_currency_from_text(raw_price_text)
    patterns = {
        "EUR": r"(?:€|eur)\s*([0-9][0-9,.\s]*)",
        "GBP": r"(?:£|gbp)\s*([0-9][0-9,.\s]*)",
        "USD": r"(?:\$|usd)\s*([0-9][0-9,.\s]*)",
    }
    pattern = patterns.get(currency or "", r"([0-9][0-9,.\s]*)")
    match = re.search(pattern, raw_price_text, flags=re.IGNORECASE)
    if not match:
        return None
    amount_text = re.sub(r"[^0-9.,]", "", match.group(1)).replace(",", "")
    try:
        amount = float(amount_text)
    except ValueError:
        return None
    return {"currency": currency or "UNK", "amount": amount}


def infer_currency_from_text(raw_price_text: str) -> str | None:
    if "€" in raw_price_text or "EUR" in raw_price_text:
        return "EUR"
    if "£" in raw_price_text or "GBP" in raw_price_text:
        return "GBP"
    if "$" in raw_price_text or "USD" in raw_price_text:
        return "USD"
    return None


def build_cluster_id(record_a: dict, record_b: dict) -> str:
    builder = normalize_simple_text(record_a.get("builder_hint") or record_b.get("builder_hint") or "unknown")
    model = normalize_simple_text(record_a.get("model_hint") or record_b.get("model_hint") or "model")
    year = record_a.get("year_hint") or record_b.get("year_hint") or "unknown"
    builder_slug = "-".join(builder.split()[:2]) or "unknown"
    model_slug = "-".join(model.split()[:3]) or "model"
    return f"cluster-{builder_slug}-{model_slug}-{year}"
