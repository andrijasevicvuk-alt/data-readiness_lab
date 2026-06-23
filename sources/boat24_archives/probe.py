from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.boat24.com"
    public_pages = [
        f"{base_url}/archive/",
        f"{base_url}/archives/",
        f"{base_url}/news/archive/",
    ]
    result = probe_source(
        source_id="boat24_archives",
        source_name="Boat24 Archives",
        base_url=base_url,
        target_confidence="guessed_url",
        target_source_note="Archive-style paths are heuristic guesses on the public Boat24 domain.",
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Archive probe checks only a few likely public archive-style URLs.",
            "If those URLs are absent, that does not imply hidden archive access should be attempted.",
        ],
    )

    all_missing_or_limited = all(
        page.status_code in {301, 302, 303, 307, 308, 404, 410}
        for page in result.page_results
    )
    any_success = any(page.status_code and 200 <= page.status_code < 300 for page in result.page_results)
    has_real_http_signal = all(page.status_code is not None for page in result.page_results)
    if (
        result.classification != "blocked_403_do_not_bypass"
        and not any_success
        and all_missing_or_limited
        and has_real_http_signal
    ):
        result.classification = "archive_not_public_or_not_found"
        result.notes.append("No obvious public archive entry point was confirmed from the small probe set.")

    return result
