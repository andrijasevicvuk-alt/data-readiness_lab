from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
JSON_OUTPUT = RESULTS_DIR / "rendered_text_probe_results.json"
CSV_OUTPUT = RESULTS_DIR / "rendered_text_probe_results.csv"


@dataclass
class RenderedTextProbeResult:
    source_name: str
    page_url: str
    raw_http_contains_croatia: bool
    rendered_text_contains_croatia: bool
    raw_http_contains_docked: bool
    rendered_text_contains_docked: bool
    rendered_text_location_phrase_found: str | None
    rendered_text_probe_notes: str


DEFAULT_RENDERED_TEXT_PROBE_RESULTS = [
    RenderedTextProbeResult(
        source_name="Marine One",
        page_url="https://www.yachtbrokerage.eu/marine-one-brokerage/fountaine-pajot-astrea-42/code-(1051)/2025",
        raw_http_contains_croatia=True,
        rendered_text_contains_croatia=True,
        raw_http_contains_docked=True,
        rendered_text_contains_docked=True,
        rendered_text_location_phrase_found="docked in croatia",
        rendered_text_probe_notes=(
            "Raw HTTP and rendered text both exposed the listing-level phrase "
            "'docked in Croatia'. Treat this as research evidence only and mark "
            "the source as requires_rendered_text_for_location until parser logic "
            "is intentionally updated."
        ),
    ),
    RenderedTextProbeResult(
        source_name="Marine One",
        page_url="https://www.yachtbrokerage.eu/boats-for-sale",
        raw_http_contains_croatia=True,
        rendered_text_contains_croatia=True,
        raw_http_contains_docked=False,
        rendered_text_contains_docked=False,
        rendered_text_location_phrase_found=None,
        rendered_text_probe_notes=(
            "Croatia appeared in general market copy on the public listing page, "
            "but no listing-level docked/moored/lying phrase was confirmed."
        ),
    ),
    RenderedTextProbeResult(
        source_name="Croatian Yachting",
        page_url="https://www.croatia-yachting.hr/en/yachts-for-sale/used-boats",
        raw_http_contains_croatia=True,
        rendered_text_contains_croatia=True,
        raw_http_contains_docked=False,
        rendered_text_contains_docked=False,
        rendered_text_location_phrase_found=None,
        rendered_text_probe_notes=(
            "The public used-boats page returned 200 and mentioned Croatia, but "
            "no listing-level location phrase such as 'docked in Croatia' was "
            "confirmed from the single rendered-text check."
        ),
    ),
]


def write_rendered_text_probe_results(results: list[RenderedTextProbeResult]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(
        json.dumps([asdict(item) for item in results], indent=2),
        encoding="utf-8",
    )
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_name",
                "page_url",
                "raw_http_contains_croatia",
                "rendered_text_contains_croatia",
                "raw_http_contains_docked",
                "rendered_text_contains_docked",
                "rendered_text_location_phrase_found",
                "rendered_text_probe_notes",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))
