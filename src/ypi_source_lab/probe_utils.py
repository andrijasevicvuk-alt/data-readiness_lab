from __future__ import annotations

import urllib.parse
import urllib.robotparser

from .detail_discovery import run_detail_discovery_probe
from .field_probe import run_field_probe
from .http_client import HttpResponse, PoliteHttpClient
from .models import DetailDiscoveryConfig, FieldProbeConfig, PageProbeResult, SourceResult


def build_robots_url(base_url: str) -> str:
    return urllib.parse.urljoin(_site_origin(base_url), "/robots.txt")


def build_sitemap_url(base_url: str) -> str:
    return urllib.parse.urljoin(_site_origin(base_url), "/sitemap.xml")


def probe_source(
    *,
    source_id: str,
    source_name: str,
    base_url: str,
    target_confidence: str,
    target_source_note: str,
    public_pages: list[str],
    client: PoliteHttpClient,
    field_probe_config: FieldProbeConfig | None = None,
    detail_discovery_config: DetailDiscoveryConfig | None = None,
    extra_notes: list[str] | None = None,
) -> SourceResult:
    robots_url = build_robots_url(base_url)
    sitemap_url = build_sitemap_url(base_url)

    robots_response = client.get(robots_url)
    sitemap_response = client.get(sitemap_url)
    robots_allows = evaluate_robots(robots_response, client.user_agent, public_pages)

    page_results: list[PageProbeResult] = []
    notes = list(extra_notes or [])

    if robots_allows is False:
        for page_url in public_pages:
            page_results.append(
                PageProbeResult(
                    url=page_url,
                    status_code=None,
                    outcome="skipped_due_to_robots",
                    reason="robots.txt disallows this probe target for the configured user agent",
                )
            )
        classification = "robots_disallow_probe_targets"
    else:
        classification = "candidate_accessible"
        for page_url in public_pages:
            response = client.get(page_url)
            page_results.append(classify_page_result(response))
            if response.status_code == 403:
                classification = "blocked_403_do_not_bypass"
                notes.append("Received HTTP 403 on a probed page. Per project rules, probing should stop here.")
                break
            if response.status_code is None and classification != "blocked_403_do_not_bypass":
                classification = "temporarily_unavailable_or_error"
            elif response.status_code and response.status_code >= 500 and classification != "blocked_403_do_not_bypass":
                classification = "temporarily_unavailable_or_error"
            elif response.status_code and 200 <= response.status_code < 300:
                continue
            elif response.status_code and 300 <= response.status_code < 500 and classification == "candidate_accessible":
                classification = "candidate_accessible_with_limits"

    if classification == "candidate_accessible" and not any(
        item.status_code and 200 <= item.status_code < 300 for item in page_results
    ):
        classification = "candidate_accessible_with_limits"

    result = SourceResult(
        source_id=source_id,
        source_name=source_name,
        base_url=base_url,
        target_confidence=target_confidence,
        target_source_note=target_source_note,
        classification=classification,
        robots_txt_url=robots_url,
        robots_txt_status_code=robots_response.status_code,
        robots_txt_accessible=robots_response.status_code == 200,
        robots_allows_probe_targets=robots_allows,
        sitemap_xml_url=sitemap_url,
        sitemap_xml_status_code=sitemap_response.status_code,
        sitemap_xml_accessible=sitemap_response.status_code == 200,
        page_results=page_results,
        notes=notes,
    )
    if field_probe_config and classification == "candidate_accessible":
        run_field_probe(client=client, source_result=result, config=field_probe_config)
    if detail_discovery_config and result.classification.startswith("candidate_"):
        run_detail_discovery_probe(client=client, source_result=result, config=detail_discovery_config)
    return result
def classify_page_result(response: HttpResponse) -> PageProbeResult:
    if response.status_code == 403:
        return PageProbeResult(
            url=response.url,
            status_code=response.status_code,
            outcome="blocked_403_do_not_bypass",
            reason="source returned HTTP 403",
        )
    if response.status_code and 200 <= response.status_code < 300:
        return PageProbeResult(
            url=response.url,
            status_code=response.status_code,
            outcome="accessible",
            reason="public page returned success",
        )
    if response.status_code and 300 <= response.status_code < 500:
        return PageProbeResult(
            url=response.url,
            status_code=response.status_code,
            outcome="limited_or_not_found",
            reason="public page returned a non-403 client response",
        )
    if response.status_code and response.status_code >= 500:
        return PageProbeResult(
            url=response.url,
            status_code=response.status_code,
            outcome="server_error",
            reason="source returned a server-side error",
        )
    return PageProbeResult(
        url=response.url,
        status_code=response.status_code,
        outcome="request_error",
        reason=response.error or "request failed",
    )


def evaluate_robots(robots_response: HttpResponse, user_agent: str, page_urls: list[str]) -> bool | None:
    if robots_response.status_code != 200 or not robots_response.body:
        return None

    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots_response.body.splitlines())
    for page_url in page_urls:
        if not parser.can_fetch(user_agent, page_url):
            return False
    return True


def _site_origin(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/"
