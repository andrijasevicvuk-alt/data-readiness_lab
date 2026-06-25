from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
DOCS_DIR = PROJECT_ROOT / "docs"

NORMALIZED_INPUT = RESULTS_DIR / "normalized_dataset_preview.json"

JSON_OUTPUT = RESULTS_DIR / "valuation_readiness_report.json"
CSV_OUTPUT = RESULTS_DIR / "valuation_readiness_report.csv"
MARKDOWN_OUTPUT = DOCS_DIR / "valuation_readiness_report.md"


@dataclass
class SourceValuationRow:
    source_name: str
    raw_record_count: int
    valuation_ready_candidate_count: int
    excluded_record_count: int
    review_required_count: int
    avg_data_quality_score: float
    builder_model_coverage_pct: float
    year_coverage_pct: float
    country_location_coverage_pct: float
    price_coverage_pct: float
    loa_coverage_pct: float
    engine_coverage_pct: float
    duplicate_risk_record_count: int
    ready_share_pct: float
    source_readiness_note: str


def main() -> int:
    payload = build_valuation_readiness_report()
    write_outputs(payload)
    print(f"Wrote {JSON_OUTPUT}")
    print(f"Wrote {CSV_OUTPUT}")
    print(f"Wrote {MARKDOWN_OUTPUT}")
    return 0


def build_valuation_readiness_report() -> dict[str, object]:
    normalized_payload = json.loads(NORMALIZED_INPUT.read_text(encoding="utf-8"))
    records = normalized_payload.get("records", [])
    source_rows = build_source_rows(records)

    summary = {
        "raw_pilot_record_count": normalized_payload.get("raw_record_count", len(records)),
        "normalized_record_count": normalized_payload.get("normalized_record_count", len(records)),
        "valuation_ready_candidate_count": sum(1 for record in records if record.get("valuation_ready_candidate")),
        "excluded_record_count": sum(1 for record in records if not record.get("valuation_ready_candidate")),
        "review_required_count": sum(1 for record in records if record.get("review_required")),
        "avg_data_quality_score": round(
            sum(record.get("data_quality_score", 0) for record in records) / len(records), 1
        )
        if records
        else 0.0,
    }

    coverage = {
        "builder_model_coverage": coverage_metric(
            records,
            lambda item: bool(item.get("canonical_builder_draft") and item.get("canonical_model_draft")),
        ),
        "year_coverage": coverage_metric(records, lambda item: item.get("year_built_draft") is not None),
        "source_coverage": build_source_coverage(records),
        "country_location_coverage": coverage_metric(
            records,
            lambda item: bool(item.get("country_draft") and item.get("location_text_draft")),
        ),
        "price_coverage": coverage_metric(
            records,
            lambda item: item.get("price_amount_draft") is not None and item.get("currency_draft") is not None,
        ),
        "loa_coverage": coverage_metric(records, lambda item: item.get("loa_m_draft") is not None),
        "engine_coverage": coverage_metric(records, lambda item: item.get("engine_signature_draft") is not None),
    }

    duplicate_summary = build_duplicate_summary(records)
    exclusion_reasons = build_reason_counts(records, "exclusion_reason")
    review_reasons = build_reason_counts(records, "review_reason")

    return {
        "summary": summary,
        "coverage": coverage,
        "duplicate_risk_summary": duplicate_summary,
        "exclusion_reason_summary": exclusion_reasons,
        "review_reason_summary": review_reasons,
        "source_breakdown": [asdict(row) for row in source_rows],
    }


def build_source_rows(records: list[dict]) -> list[SourceValuationRow]:
    by_source: dict[str, list[dict]] = {}
    for record in records:
        by_source.setdefault(record["source_name"], []).append(record)

    rows: list[SourceValuationRow] = []
    for source_name, source_records in sorted(by_source.items()):
        record_count = len(source_records)
        ready_count = sum(1 for record in source_records if record.get("valuation_ready_candidate"))
        excluded_count = record_count - ready_count
        review_count = sum(1 for record in source_records if record.get("review_required"))
        avg_score = (
            round(sum(record.get("data_quality_score", 0) for record in source_records) / record_count, 1)
            if record_count
            else 0.0
        )

        rows.append(
            SourceValuationRow(
                source_name=source_name,
                raw_record_count=record_count,
                valuation_ready_candidate_count=ready_count,
                excluded_record_count=excluded_count,
                review_required_count=review_count,
                avg_data_quality_score=avg_score,
                builder_model_coverage_pct=coverage_pct(
                    source_records,
                    lambda item: bool(item.get("canonical_builder_draft") and item.get("canonical_model_draft")),
                ),
                year_coverage_pct=coverage_pct(
                    source_records,
                    lambda item: item.get("year_built_draft") is not None,
                ),
                country_location_coverage_pct=coverage_pct(
                    source_records,
                    lambda item: bool(item.get("country_draft") and item.get("location_text_draft")),
                ),
                price_coverage_pct=coverage_pct(
                    source_records,
                    lambda item: item.get("price_amount_draft") is not None and item.get("currency_draft") is not None,
                ),
                loa_coverage_pct=coverage_pct(
                    source_records,
                    lambda item: item.get("loa_m_draft") is not None,
                ),
                engine_coverage_pct=coverage_pct(
                    source_records,
                    lambda item: item.get("engine_signature_draft") is not None,
                ),
                duplicate_risk_record_count=sum(
                    1 for item in source_records if item.get("duplicate_confidence") in {"high", "medium", "low"}
                ),
                ready_share_pct=round((ready_count / record_count) * 100, 1) if record_count else 0.0,
                source_readiness_note=build_source_note(source_name, ready_count, excluded_count, source_records),
            )
        )

    rows.sort(key=lambda row: (-row.ready_share_pct, -row.avg_data_quality_score, row.source_name.lower()))
    return rows


def build_source_note(source_name: str, ready_count: int, excluded_count: int, records: list[dict]) -> str:
    if source_name == "TheYachtMarket":
        return "Best current backbone candidate; normalized fields are strong enough to prove valuation usefulness."
    if source_name == "Marine One / YachtBrokerage":
        if excluded_count == len(records):
            return "Good trust-anchor source, but location coverage and duplicate review still block valuation-ready promotion."
        return "Trust-anchor source with partial readiness; needs manual review before transfer."
    return f"{ready_count} ready / {excluded_count} excluded in the current tiny sample."


def coverage_metric(records: list[dict], predicate) -> dict[str, object]:
    present = sum(1 for record in records if predicate(record))
    total = len(records)
    return {
        "present_count": present,
        "total_count": total,
        "coverage_pct": round((present / total) * 100, 1) if total else 0.0,
    }


def coverage_pct(records: list[dict], predicate) -> float:
    metric = coverage_metric(records, predicate)
    return float(metric["coverage_pct"])


def build_source_coverage(records: list[dict]) -> list[dict[str, object]]:
    by_source: dict[str, int] = {}
    total = len(records)
    for record in records:
        by_source[record["source_name"]] = by_source.get(record["source_name"], 0) + 1

    rows = []
    for source_name, count in sorted(by_source.items()):
        rows.append(
            {
                "source_name": source_name,
                "record_count": count,
                "share_pct": round((count / total) * 100, 1) if total else 0.0,
            }
        )
    return rows


def build_duplicate_summary(records: list[dict]) -> dict[str, object]:
    clusters: dict[str, list[dict]] = {}
    for record in records:
        if record.get("duplicate_confidence") == "none":
            continue
        clusters.setdefault(record["duplicate_cluster_id_suggestion"], []).append(record)

    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for record in records:
        confidence = record.get("duplicate_confidence")
        if confidence in confidence_counts:
            confidence_counts[confidence] += 1

    return {
        "risky_record_count": sum(confidence_counts.values()),
        "high_confidence_record_count": confidence_counts["high"],
        "medium_confidence_record_count": confidence_counts["medium"],
        "low_confidence_record_count": confidence_counts["low"],
        "cluster_count": len(clusters),
        "clusters": [
            {
                "cluster_id": cluster_id,
                "member_count": len(cluster_records),
                "member_urls": [item["listing_url"] for item in cluster_records],
                "highest_confidence": max(
                    (item["duplicate_confidence"] for item in cluster_records),
                    key=duplicate_confidence_rank,
                    default="none",
                ),
            }
            for cluster_id, cluster_records in sorted(clusters.items())
        ],
    }


def build_reason_counts(records: list[dict], field_name: str) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for record in records:
        value = record.get(field_name)
        if not value:
            continue
        for part in str(value).split(";"):
            reason = part.strip()
            if not reason:
                continue
            counts[reason] = counts.get(reason, 0) + 1
    return [
        {"reason": reason, "count": count}
        for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def duplicate_confidence_rank(value: str) -> int:
    order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    return order.get(value, 0)


def write_outputs(payload: dict[str, object]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    JSON_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = payload.get("source_breakdown", [])
    fieldnames = list(SourceValuationRow.__dataclass_fields__.keys())
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    MARKDOWN_OUTPUT.write_text(build_markdown_report(payload), encoding="utf-8")


def build_markdown_report(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    coverage = payload["coverage"]
    duplicate_summary = payload["duplicate_risk_summary"]
    source_breakdown = payload["source_breakdown"]

    lines = [
        "# Valuation Readiness Report",
        "",
        "This report checks whether the tiny source-lab sample already looks strong enough to become valuation-ready raw material for the main YPI project.",
        "",
        "## Summary",
        "",
        f"- Raw pilot records: `{summary['raw_pilot_record_count']}`",
        f"- Normalized preview records: `{summary['normalized_record_count']}`",
        f"- Valuation-ready candidate records: `{summary['valuation_ready_candidate_count']}`",
        f"- Excluded records: `{summary['excluded_record_count']}`",
        f"- Review-required records: `{summary['review_required_count']}`",
        f"- Average data quality score: `{summary['avg_data_quality_score']}`",
        "",
        "## Coverage",
        "",
        f"- Builder/model coverage: `{coverage['builder_model_coverage']['present_count']}/{coverage['builder_model_coverage']['total_count']}` ({coverage['builder_model_coverage']['coverage_pct']}%)",
        f"- Year coverage: `{coverage['year_coverage']['present_count']}/{coverage['year_coverage']['total_count']}` ({coverage['year_coverage']['coverage_pct']}%)",
        f"- Country/location coverage: `{coverage['country_location_coverage']['present_count']}/{coverage['country_location_coverage']['total_count']}` ({coverage['country_location_coverage']['coverage_pct']}%)",
        f"- Price coverage: `{coverage['price_coverage']['present_count']}/{coverage['price_coverage']['total_count']}` ({coverage['price_coverage']['coverage_pct']}%)",
        f"- LOA coverage: `{coverage['loa_coverage']['present_count']}/{coverage['loa_coverage']['total_count']}` ({coverage['loa_coverage']['coverage_pct']}%)",
        f"- Engine coverage: `{coverage['engine_coverage']['present_count']}/{coverage['engine_coverage']['total_count']}` ({coverage['engine_coverage']['coverage_pct']}%)",
        "",
        "## Duplicate Risk",
        "",
        f"- Risky records: `{duplicate_summary['risky_record_count']}`",
        f"- Duplicate clusters: `{duplicate_summary['cluster_count']}`",
        f"- High-confidence risky records: `{duplicate_summary['high_confidence_record_count']}`",
        f"- Medium-confidence risky records: `{duplicate_summary['medium_confidence_record_count']}`",
        f"- Low-confidence risky records: `{duplicate_summary['low_confidence_record_count']}`",
        "",
        "## Source Breakdown",
        "",
        "| Source | Raw Records | Ready | Excluded | Avg Score | Location Coverage | Engine Coverage | Duplicate Risk | Note |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in source_breakdown:
        lines.append(
            f"| {row['source_name']} | {row['raw_record_count']} | {row['valuation_ready_candidate_count']} | "
            f"{row['excluded_record_count']} | {row['avg_data_quality_score']} | {row['country_location_coverage_pct']}% | "
            f"{row['engine_coverage_pct']}% | {row['duplicate_risk_record_count']} | {row['source_readiness_note']} |"
        )

    lines.extend(["", "## Recommendation", ""])
    if summary["valuation_ready_candidate_count"] >= 3:
        lines.append(
            "- The current direction is strong enough to prove a useful YPI valuation MVP, but it still needs duplicate review and wider location coverage before promotion into the main repo."
        )
    else:
        lines.append(
            "- The direction is promising, but the current sample is still too thin to prove a useful YPI valuation MVP without expanding the stable source pair."
        )
    lines.append(
        "- TheYachtMarket remains the best backbone candidate, while Marine One remains the best trust-anchor candidate that still needs review-oriented hardening."
    )

    return "\n".join(lines)
