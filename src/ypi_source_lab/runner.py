from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from .detail_discovery import summarize_detail_discovery_rows
from .field_probe import summarize_field_probe_rows
from .http_client import PoliteHttpClient
from .models import SourceResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = PROJECT_ROOT / "sources"
RESULTS_DIR = PROJECT_ROOT / "results"
JSON_OUTPUT = RESULTS_DIR / "source_tests.json"
CSV_OUTPUT = RESULTS_DIR / "source_tests.csv"
FIELD_JSON_OUTPUT = RESULTS_DIR / "field_probe_results.json"
FIELD_CSV_OUTPUT = RESULTS_DIR / "field_probe_results.csv"
DETAIL_JSON_OUTPUT = RESULTS_DIR / "detail_discovery_results.json"
DETAIL_CSV_OUTPUT = RESULTS_DIR / "detail_discovery_results.csv"


def main() -> int:
    client = PoliteHttpClient()
    results = run_all_probes(client)
    write_results(results)
    print(f"Wrote {JSON_OUTPUT}")
    print(f"Wrote {CSV_OUTPUT}")
    print(f"Wrote {FIELD_JSON_OUTPUT}")
    print(f"Wrote {FIELD_CSV_OUTPUT}")
    print(f"Wrote {DETAIL_JSON_OUTPUT}")
    print(f"Wrote {DETAIL_CSV_OUTPUT}")
    return 0


def run_all_probes(client: PoliteHttpClient) -> list[SourceResult]:
    results: list[SourceResult] = []
    for probe_path in sorted(SOURCES_DIR.glob("*/probe.py")):
        module = load_module_from_path(probe_path)
        if not hasattr(module, "run_probe"):
            raise RuntimeError(f"Probe file missing run_probe(): {probe_path}")
        result = module.run_probe(client)
        results.append(result)
    return results


def load_module_from_path(path: Path) -> ModuleType:
    module_name = "probe_" + "_".join(path.parts[-2:]).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def write_results(results: list[SourceResult]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    json_payload = [result.to_dict() for result in results]
    JSON_OUTPUT.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source_id",
                "source_name",
                "base_url",
                "target_confidence",
                "target_source_note",
                "classification",
                "robots_txt_status_code",
                "robots_txt_accessible",
                "robots_allows_probe_targets",
                "sitemap_xml_status_code",
                "sitemap_xml_accessible",
                "field_probe_attempted",
                "listing_pages_tested",
                "price_signal_visible",
                "year_signal_visible",
                "location_signal_visible",
                "engine_signal_visible",
                "stable_listing_url_visible",
                "raw_html_contains_structured_data",
                "field_probe_notes",
                "detail_discovery_attempted",
                "probable_detail_pages_found",
                "detail_discovery_notes",
                "tested_pages",
                "page_status_codes",
                "notes",
            ]
        )
        for result in results:
            writer.writerow(
                [
                    result.source_id,
                    result.source_name,
                    result.base_url,
                    result.target_confidence,
                    result.target_source_note,
                    result.classification,
                    result.robots_txt_status_code,
                    result.robots_txt_accessible,
                    result.robots_allows_probe_targets,
                    result.sitemap_xml_status_code,
                    result.sitemap_xml_accessible,
                    result.field_probe_attempted,
                    result.listing_pages_tested,
                    result.price_signal_visible,
                    result.year_signal_visible,
                    result.location_signal_visible,
                    result.engine_signal_visible,
                    result.stable_listing_url_visible,
                    result.raw_html_contains_structured_data,
                    " | ".join(result.field_probe_notes),
                    result.detail_discovery_attempted,
                    result.probable_detail_pages_found,
                    " | ".join(result.detail_discovery_notes),
                    " | ".join(page.url for page in result.page_results),
                    " | ".join(str(page.status_code) for page in result.page_results),
                    " | ".join(result.notes),
                ]
            )

    field_rows = summarize_field_probe_rows(results)
    FIELD_JSON_OUTPUT.write_text(json.dumps(field_rows, indent=2), encoding="utf-8")

    with FIELD_CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(field_rows[0].keys()) if field_rows else [
            "source_id",
            "source_name",
            "classification",
            "page_type",
            "url",
            "status_code",
            "title_signal_visible",
            "asking_price_signal_visible",
            "currency_signal_visible",
            "builder_brand_signal_visible",
            "model_signal_visible",
            "year_signal_visible",
            "location_signal_visible",
            "engine_signal_visible",
            "length_signal_visible",
            "stable_listing_url_visible",
            "stable_listing_id_signal_visible",
            "image_presence_visible",
            "image_count_estimate",
            "raw_html_contains_structured_data",
            "notes",
        ])
        writer.writeheader()
        writer.writerows(field_rows)

    detail_rows = summarize_detail_discovery_rows(results)
    DETAIL_JSON_OUTPUT.write_text(json.dumps(detail_rows, indent=2), encoding="utf-8")

    with DETAIL_CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(detail_rows[0].keys()) if detail_rows else [
                "source_id",
                "source_name",
                "classification",
                "source_page_url",
                "candidate_detail_url",
                "link_text_sample",
                "url_pattern_reason",
                "http_status",
                "final_url",
                "is_probable_detail_page",
                "rejection_reason",
            ],
        )
        writer.writeheader()
        writer.writerows(detail_rows)
