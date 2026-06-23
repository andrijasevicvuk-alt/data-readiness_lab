from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
DOCS_DIR = PROJECT_ROOT / "docs"

SOURCE_TESTS_PATH = RESULTS_DIR / "source_tests.json"
FIELD_PROBE_PATH = RESULTS_DIR / "field_probe_results.json"
DETAIL_DISCOVERY_PATH = RESULTS_DIR / "detail_discovery_results.json"
RENDERED_TEXT_PATH = RESULTS_DIR / "rendered_text_probe_results.json"
MARINE_ONE_PARSER_PATH = RESULTS_DIR / "marine_one_parser_sample.json"
THEYACHTMARKET_PARSER_PATH = RESULTS_DIR / "theyachtmarket_parser_sample.json"

JSON_OUTPUT = RESULTS_DIR / "source_readiness_report.json"
CSV_OUTPUT = RESULTS_DIR / "source_readiness_report.csv"
MARKDOWN_OUTPUT = DOCS_DIR / "source_readiness_report.md"


@dataclass
class SourceReadinessRow:
    source_name: str
    access_status: str
    final_classification: str
    homepage_status: str
    listing_page_status: str
    robots_txt_status: str
    sitemap_status: str
    detail_discovery_status: str
    parser_status: str
    parsed_sample_count: int
    title_field_status: str
    price_field_status: str
    currency_field_status: str
    builder_model_field_status: str
    year_field_status: str
    location_field_status: str
    loa_field_status: str
    engine_field_status: str
    image_field_status: str
    rendering_required: str
    blocker_summary: str
    ypi_role_candidate: str
    recommended_next_action: str
    readiness_rank: int


def main() -> int:
    rows = build_source_readiness_rows()
    write_outputs(rows)
    print(f"Wrote {JSON_OUTPUT}")
    print(f"Wrote {CSV_OUTPUT}")
    print(f"Wrote {MARKDOWN_OUTPUT}")
    return 0


def build_source_readiness_rows() -> list[SourceReadinessRow]:
    source_tests = load_json(SOURCE_TESTS_PATH)
    field_probe_rows = load_json(FIELD_PROBE_PATH)
    detail_rows = load_json(DETAIL_DISCOVERY_PATH)
    rendered_rows = load_json(RENDERED_TEXT_PATH)
    marine_parser = load_optional_json(MARINE_ONE_PARSER_PATH)
    tym_parser = load_optional_json(THEYACHTMARKET_PARSER_PATH)

    parser_payloads = {
        "Marine One": marine_parser,
        "Marine One / YachtBrokerage": marine_parser,
        "TheYachtMarket": tym_parser,
    }

    field_by_source: dict[str, list[dict]] = {}
    for item in field_probe_rows:
        field_by_source.setdefault(item["source_name"], []).append(item)

    detail_by_source: dict[str, list[dict]] = {}
    for item in detail_rows:
        detail_by_source.setdefault(item["source_name"], []).append(item)

    rendered_by_source: dict[str, list[dict]] = {}
    for item in rendered_rows:
        rendered_by_source.setdefault(item["source_name"], []).append(item)

    rows: list[SourceReadinessRow] = []
    for source in source_tests:
        source_name = source["source_name"]
        parser_payload = parser_payloads.get(source_name)
        final_classification = parser_payload.get("parser_status") if parser_payload else source["classification"]

        homepage_status = page_status_for_type(source, "homepage")
        listing_status = page_status_for_type(source, "listing")
        if listing_status == "not_tested":
            listing_status = fallback_listing_status(source)

        parser_status = parser_payload.get("parser_status", "not_run") if parser_payload else "not_run"
        parsed_sample_count = int(parser_payload.get("detail_pages_parsed", 0)) if parser_payload else 0

        field_statuses = derive_field_statuses(source, parser_payload, field_by_source.get(source_name, []))
        rendering_required = derive_rendering_required(source, rendered_by_source.get(source_name, []))
        detail_discovery_status = derive_detail_discovery_status(source, detail_by_source.get(source_name, []))
        access_status = derive_access_status(source)
        blocker_summary = derive_blocker_summary(source, parser_payload, rendering_required)
        ypi_role_candidate = derive_role_candidate(source, parser_payload)
        recommended_next_action = derive_next_action(source, parser_payload)

        rows.append(
            SourceReadinessRow(
                source_name=source_name,
                access_status=access_status,
                final_classification=final_classification,
                homepage_status=homepage_status,
                listing_page_status=listing_status,
                robots_txt_status=status_label(source.get("robots_txt_status_code")),
                sitemap_status=status_label(source.get("sitemap_xml_status_code")),
                detail_discovery_status=detail_discovery_status,
                parser_status=parser_status,
                parsed_sample_count=parsed_sample_count,
                title_field_status=field_statuses["title"],
                price_field_status=field_statuses["price"],
                currency_field_status=field_statuses["currency"],
                builder_model_field_status=field_statuses["builder_model"],
                year_field_status=field_statuses["year"],
                location_field_status=field_statuses["location"],
                loa_field_status=field_statuses["loa"],
                engine_field_status=field_statuses["engine"],
                image_field_status=field_statuses["image"],
                rendering_required=rendering_required,
                blocker_summary=blocker_summary,
                ypi_role_candidate=ypi_role_candidate,
                recommended_next_action=recommended_next_action,
                readiness_rank=derive_readiness_rank(source_name, final_classification, ypi_role_candidate),
            )
        )

    rows.sort(key=lambda item: (item.readiness_rank, item.source_name.lower()))
    return rows


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def page_status_for_type(source: dict, page_type: str) -> str:
    for page in source.get("field_probe_page_results", []):
        if page.get("page_type") == page_type:
            return status_label(page.get("status_code"))
    return "not_tested"


def fallback_listing_status(source: dict) -> str:
    pages = source.get("page_results", [])
    if len(pages) >= 2:
        return status_label(pages[1].get("status_code"))
    return "not_tested"


def status_label(code: int | None) -> str:
    if code is None:
        return "not_tested"
    return str(code)


def derive_access_status(source: dict) -> str:
    classification = source["classification"]
    if classification == "blocked_403_do_not_bypass":
        return "blocked"
    if any((page.get("status_code") or 0) == 200 for page in source.get("page_results", [])):
        return "reachable_public_200"
    return "limited_or_inconclusive"


def derive_field_statuses(source: dict, parser_payload: dict, field_probe_rows: list[dict]) -> dict[str, str]:
    if parser_payload:
        listings = parser_payload.get("listings", [])
        return {
            "title": parser_consensus(listings, "raw_title"),
            "price": parser_consensus(listings, "raw_price_text"),
            "currency": parser_consensus(listings, "currency_hint"),
            "builder_model": parser_builder_model_consensus(listings),
            "year": parser_consensus(listings, "year_hint"),
            "location": parser_consensus(listings, "location_hint"),
            "loa": parser_consensus(listings, "loa_hint"),
            "engine": parser_consensus(listings, "engine_hint"),
            "image": parser_boolean_consensus(listings, "image_present"),
        }

    detail_rows = [item for item in field_probe_rows if item.get("page_type") == "detail" and item.get("status_code") == 200]
    candidate_rows = detail_rows or [item for item in field_probe_rows if item.get("page_type") in {"listing", "homepage"}]
    if not candidate_rows:
        default = "not_tested"
        return {
            "title": default,
            "price": default,
            "currency": default,
            "builder_model": default,
            "year": default,
            "location": default,
            "loa": default,
            "engine": default,
            "image": default,
        }

    return {
        "title": probe_boolean_status(candidate_rows, "title_signal_visible"),
        "price": probe_boolean_status(candidate_rows, "asking_price_signal_visible"),
        "currency": probe_boolean_status(candidate_rows, "currency_signal_visible"),
        "builder_model": combine_probe_statuses(
            probe_boolean_status(candidate_rows, "builder_brand_signal_visible"),
            probe_boolean_status(candidate_rows, "model_signal_visible"),
        ),
        "year": probe_boolean_status(candidate_rows, "year_signal_visible"),
        "location": probe_boolean_status(candidate_rows, "location_signal_visible"),
        "loa": probe_boolean_status(candidate_rows, "length_signal_visible"),
        "engine": probe_boolean_status(candidate_rows, "engine_signal_visible"),
        "image": probe_boolean_status(candidate_rows, "image_presence_visible"),
    }


def parser_consensus(listings: list[dict], field_name: str) -> str:
    if not listings:
        return "not_tested"
    present = sum(1 for item in listings if item.get(field_name))
    if present == len(listings):
        return "parsed_strong"
    if present > 0:
        return "parsed_partial"
    return "missing"


def parser_builder_model_consensus(listings: list[dict]) -> str:
    if not listings:
        return "not_tested"
    present = sum(1 for item in listings if item.get("builder_hint") and item.get("model_hint"))
    if present == len(listings):
        return "parsed_strong"
    if present > 0:
        return "parsed_partial"
    return "missing"


def parser_boolean_consensus(listings: list[dict], field_name: str) -> str:
    if not listings:
        return "not_tested"
    positive = sum(1 for item in listings if item.get(field_name) is True)
    if positive == len(listings):
        return "parsed_strong"
    if positive > 0:
        return "parsed_partial"
    return "missing"


def probe_boolean_status(rows: list[dict], field_name: str) -> str:
    positive = sum(1 for row in rows if row.get(field_name) is True)
    if positive == len(rows):
        return "signal_visible"
    if positive > 0:
        return "signal_partial"
    return "missing"


def combine_probe_statuses(left: str, right: str) -> str:
    if left == "signal_visible" and right == "signal_visible":
        return "signal_visible"
    if "partial" in left or "partial" in right or left == "signal_visible" or right == "signal_visible":
        return "signal_partial"
    if left == "not_tested" and right == "not_tested":
        return "not_tested"
    return "missing"


def derive_rendering_required(source: dict, rendered_rows: list[dict]) -> str:
    classification = source["classification"]
    if classification in {
        "candidate_accessible_needs_browser_rendering",
        "candidate_requires_rendering_for_detail_links",
    }:
        return "yes"
    if source["source_name"] == "Marine One" and rendered_rows:
        if any(item.get("rendered_text_location_phrase_found") for item in rendered_rows):
            return "partial_for_location"
    return "no"


def derive_detail_discovery_status(source: dict, detail_rows: list[dict]) -> str:
    if source.get("detail_discovery_attempted") is False:
        return "not_run"
    probable = source.get("probable_detail_pages_found", 0)
    if probable > 0:
        return f"probable_{probable}"
    if detail_rows:
        return "tested_none_probable"
    return "no_candidates_in_raw_html"


def derive_blocker_summary(source: dict, parser_payload: dict, rendering_required: str) -> str:
    classification = source["classification"]
    if classification == "blocked_403_do_not_bypass":
        return "HTTP 403 stop signal; do not bypass."
    if parser_payload:
        parser_status = parser_payload.get("parser_status")
        if parser_status == "parser_prototype_success":
            missing_broker = any(item.get("broker_hint") is None for item in parser_payload.get("listings", []))
            if missing_broker:
                return "Core parser fields are strong; broker field remains weak or missing."
            return "No major blocker in the tiny proven sample."
        if parser_status == "parser_prototype_partial":
            return "Core fields parse, but important fields remain weak or missing."
    if rendering_required == "yes":
        return "Raw HTML discovery is incomplete; browser-visible rendering likely needed."
    if classification == "candidate_detail_discovery_partial":
        return "Deeper links were found, but they still resolved to category-like pages."
    if classification == "candidate_accessible_fields_weak":
        return "Signals exist, but stable public detail-page evidence is still weak."
    return "No parser-ready public detail flow has been proven yet."


def derive_role_candidate(source: dict, parser_payload: dict) -> str:
    source_name = source["source_name"]
    classification = source["classification"]
    parser_status = parser_payload.get("parser_status") if parser_payload else None
    if classification == "blocked_403_do_not_bypass":
        return "blocked_do_not_bypass"
    if source_name == "TheYachtMarket" and parser_status == "parser_prototype_success":
        return "broader_marketplace_backbone"
    if source_name == "Marine One" and parser_status == "parser_prototype_partial":
        return "local_broker_trust_anchor"
    if source_name in {"Njuškalo Nautika", "Burza Nautike"}:
        return "local_classifieds_anchor" if classification == "candidate_detail_discovery_partial" else "delayed_rendering_candidate"
    if classification in {"candidate_accessible_needs_browser_rendering", "candidate_requires_rendering_for_detail_links"}:
        return "delayed_rendering_candidate"
    return "not_ready"


def derive_next_action(source: dict, parser_payload: dict) -> str:
    source_name = source["source_name"]
    classification = source["classification"]
    parser_status = parser_payload.get("parser_status") if parser_payload else None

    if classification == "blocked_403_do_not_bypass":
        if source_name == "Boat24":
            return "Do not use for MVP; revisit only through permission/feed/API or future research."
        return "Hold; do not bypass. Revisit only with permission/feed/API access."
    if source_name == "TheYachtMarket" and parser_status == "parser_prototype_success":
        return "Promote to adapter candidate #1 and use as the first broader marketplace backbone."
    if source_name == "Marine One" and parser_status == "parser_prototype_partial":
        return "Promote to adapter candidate #2 and harden location/engine only within current safe scope."
    if classification == "candidate_accessible_needs_browser_rendering":
        return "Delay until a small rendering-aware discovery step is explicitly approved."
    if classification == "candidate_requires_rendering_for_detail_links":
        return "Delay; only revisit if a safe rendering-based link-discovery check is later justified."
    if classification == "candidate_detail_discovery_partial":
        return "Delay parser work; retry only with a tiny stricter detail-discovery pass later."
    if classification == "candidate_accessible_fields_weak":
        return "Delay until stable public detail-page evidence is proven."
    return "Keep as research-only; no immediate adapter work."


def derive_readiness_rank(source_name: str, final_classification: str, role: str) -> int:
    if source_name == "TheYachtMarket":
        return 1
    if source_name == "Marine One":
        return 2
    if role == "delayed_rendering_candidate":
        return 4
    if role == "local_classifieds_anchor":
        return 5
    if role == "blocked_do_not_bypass":
        return 9
    return 6


def write_outputs(rows: list[SourceReadinessRow]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    JSON_OUTPUT.write_text(
        json.dumps([asdict(item) for item in rows], indent=2),
        encoding="utf-8",
    )

    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else list(SourceReadinessRow.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    MARKDOWN_OUTPUT.write_text(build_markdown_report(rows), encoding="utf-8")


def build_markdown_report(rows: list[SourceReadinessRow]) -> str:
    top_lines = [
        "# Source Readiness Report",
        "",
        "This report consolidates the current access, discovery, rendering, and parser evidence across all tested sources.",
        "",
        "## Current Best Pair",
        "",
        "- TheYachtMarket is the first broader marketplace backbone candidate.",
        "- Marine One is the first local broker trust-anchor candidate.",
        "- Boat24 is not required for MVP if TheYachtMarket remains stable.",
        "- Boat24 may still be useful later through permission/feed/API access or future research.",
        "",
        "## Source Ranking",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        top_lines.append(
            f"{index}. {row.source_name}: `{row.final_classification}`; "
            f"role `{row.ypi_role_candidate}`; next `{row.recommended_next_action}`"
        )

    top_lines.extend(
        [
            "",
            "## Table",
            "",
            "| Source | Final Classification | Role Candidate | Parser | Parsed Sample | Location | Engine | Rendering Required | Next Action |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        top_lines.append(
            f"| {row.source_name} | `{row.final_classification}` | `{row.ypi_role_candidate}` | `{row.parser_status}` | "
            f"{row.parsed_sample_count} | {row.location_field_status} | {row.engine_field_status} | {row.rendering_required} | {row.recommended_next_action} |"
        )

    top_lines.extend(["", "## Per Source", ""])
    for row in rows:
        top_lines.extend(
            [
                f"### {row.source_name}",
                "",
                f"- Access status: `{row.access_status}`",
                f"- Final classification: `{row.final_classification}`",
                f"- Role candidate: `{row.ypi_role_candidate}`",
                f"- Detail discovery: `{row.detail_discovery_status}`",
                f"- Parser status: `{row.parser_status}` with sample count `{row.parsed_sample_count}`",
                f"- Field summary: title `{row.title_field_status}`, price `{row.price_field_status}`, currency `{row.currency_field_status}`, builder/model `{row.builder_model_field_status}`, year `{row.year_field_status}`, location `{row.location_field_status}`, LOA `{row.loa_field_status}`, engine `{row.engine_field_status}`, image `{row.image_field_status}`",
                f"- Rendering required: `{row.rendering_required}`",
                f"- Blocker summary: {row.blocker_summary}",
                f"- Recommended next action: {row.recommended_next_action}",
                "",
            ]
        )
    return "\n".join(top_lines)
