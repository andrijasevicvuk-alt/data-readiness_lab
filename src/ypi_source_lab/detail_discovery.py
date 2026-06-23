from __future__ import annotations

import html
import re

from .field_probe import (
    LinkExtractor,
    extract_title,
    is_same_origin,
    is_stable_listing_url,
    normalize_url,
    strip_fragment,
    strip_tags,
    strip_trailing_slash,
)
from .http_client import HttpResponse, PoliteHttpClient
from .models import DetailDiscoveryCandidateResult, DetailDiscoveryConfig, SourceResult


def run_detail_discovery_probe(
    *,
    client: PoliteHttpClient,
    source_result: SourceResult,
    config: DetailDiscoveryConfig,
) -> None:
    source_result.detail_discovery_attempted = True

    page_responses = []
    for page_url in [config.homepage_url, config.discovery_page_url]:
        response = client.get(page_url, max_bytes=350_000)
        page_responses.append(response)

    candidates = discover_candidate_links(page_responses, config)
    if not candidates:
        source_result.detail_discovery_notes.append(
            "No candidate detail links were confirmed from raw HTML on the tested public pages."
        )

    results: list[DetailDiscoveryCandidateResult] = []
    for candidate in candidates[: config.max_candidate_links]:
        response = client.get(candidate["candidate_detail_url"], max_bytes=250_000)
        probable, rejection_reason = evaluate_probable_detail_page(
            response=response,
            config=config,
            discovery_page_url=candidate["source_page_url"],
        )
        results.append(
            DetailDiscoveryCandidateResult(
                source_name=source_result.source_name,
                source_page_url=candidate["source_page_url"],
                candidate_detail_url=candidate["candidate_detail_url"],
                link_text_sample=candidate["link_text_sample"],
                url_pattern_reason=candidate["url_pattern_reason"],
                http_status=response.status_code,
                final_url=response.final_url,
                is_probable_detail_page=probable,
                rejection_reason=rejection_reason,
            )
        )

    source_result.detail_discovery_results = results
    source_result.probable_detail_pages_found = sum(1 for item in results if item.is_probable_detail_page)
    if results:
        source_result.detail_discovery_notes.append(
            f"Tested {len(results)} candidate detail link(s); probable detail pages found: "
            f"{source_result.probable_detail_pages_found}."
        )

    source_result.classification = classify_detail_discovery(source_result, page_responses)


def discover_candidate_links(
    page_responses: list[HttpResponse],
    config: DetailDiscoveryConfig,
) -> list[dict[str, str]]:
    preferred_texts = [item.lower() for item in config.preferred_anchor_texts]
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()

    for response in page_responses:
        if response.status_code != 200 or not response.body:
            continue

        parser = LinkExtractor()
        parser.feed(response.body)

        for link in parser.links:
            href = link.get("href", "").strip()
            text = link.get("text", "").strip()
            absolute_url = normalize_url(response.url, href)
            if not absolute_url:
                continue
            if not is_same_origin(response.url, absolute_url):
                continue

            cleaned_url = strip_fragment(absolute_url)
            if cleaned_url in {
                strip_trailing_slash(config.homepage_url),
                strip_trailing_slash(config.discovery_page_url),
            }:
                continue
            if any(fragment.lower() in cleaned_url.lower() for fragment in config.detail_url_deny_contain):
                continue

            url_reason = first_matching_reason(cleaned_url, config.detail_url_must_contain, "url_match")
            text_reason = first_matching_reason(text.lower(), preferred_texts, "anchor_text_match")
            if config.detail_url_must_contain and not url_reason:
                continue
            if not url_reason and not text_reason:
                continue

            if cleaned_url in seen:
                continue
            seen.add(cleaned_url)
            candidates.append(
                {
                    "source_page_url": response.url,
                    "candidate_detail_url": cleaned_url,
                    "link_text_sample": text[:120],
                    "url_pattern_reason": url_reason or text_reason or "raw_anchor_link",
                    "_rank": build_candidate_rank(
                        candidate_url=cleaned_url,
                        source_page_url=response.url,
                        url_reason=url_reason,
                        text_reason=text_reason,
                    ),
                }
            )

    candidates.sort(key=lambda item: item["_rank"], reverse=True)
    return candidates


def evaluate_probable_detail_page(
    *,
    response: HttpResponse,
    config: DetailDiscoveryConfig,
    discovery_page_url: str,
) -> tuple[bool, str | None]:
    if response.status_code != 200:
        return False, "candidate did not return HTTP 200"

    normalized_text = normalize_text(response.body)
    final_url = strip_fragment(response.final_url)
    title = extract_title(response.body)
    lower_title = title.lower()

    if final_url in {
        strip_trailing_slash(config.homepage_url),
        strip_trailing_slash(config.discovery_page_url),
    }:
        return False, "candidate redirected back to the homepage or the tested category page"

    if "captcha" in lower_title or "shieldsquare" in normalized_text:
        return False, "candidate returned an anti-bot challenge page rather than a listing detail page"

    if "404" in lower_title or "page not found" in normalized_text or "stranica nije prona" in normalized_text:
        return False, "candidate returned a not-found page rather than a listing detail page"

    if is_obvious_category_page(final_url, title, normalized_text):
        return False, "candidate appears to be another category/search/brand page rather than a unique listing"

    price_visible = bool(re.search(r"(\u20ac|\beur\b|\$|\busd\b|\bgbp\b)\s*[0-9][0-9., ]+", normalized_text))
    year_visible = bool(re.search(r"\b(19|20)\d{2}\b", normalized_text))
    boat_signal_visible = bool(
        re.search(r"\b(yacht|boat|catamaran|sailboat|motorboat|gulet|rib)\b", normalized_text)
    )
    stable_url_visible = is_stable_listing_url(final_url)
    unique_title_visible = bool(title) and not any(
        marker in lower_title
        for marker in [
            "boats for sale",
            "broker directory",
            "search",
            "nautika",
            "plovila",
            "croatia",
        ]
    )

    positive_signals = sum(
        [
            unique_title_visible,
            price_visible,
            year_visible,
            boat_signal_visible,
            stable_url_visible,
        ]
    )
    probable = stable_url_visible and unique_title_visible and positive_signals >= 4
    if probable:
        return True, None
    return False, "candidate lacked enough detail-page evidence in raw HTML"


def classify_detail_discovery(
    source_result: SourceResult,
    page_responses: list[HttpResponse],
) -> str:
    probable_count = source_result.probable_detail_pages_found
    tested_count = len(source_result.detail_discovery_results)

    if probable_count >= 2:
        return "candidate_detail_discovery_success"
    if probable_count == 1:
        return "candidate_detail_discovery_partial"

    if tested_count > 0:
        if any(
            item.rejection_reason and "category/search/brand page" in item.rejection_reason
            for item in source_result.detail_discovery_results
        ):
            return "candidate_detail_discovery_partial"
        return "candidate_detail_discovery_failed"

    if any(is_render_shell_response(response) for response in page_responses):
        return "candidate_requires_rendering_for_detail_links"
    return "candidate_detail_discovery_failed"


def first_matching_reason(raw_value: str, candidates: list[str], prefix: str) -> str | None:
    for candidate in candidates:
        if candidate.lower() in raw_value.lower():
            return f"{prefix}:{candidate}"
    return None


def build_candidate_rank(
    *,
    candidate_url: str,
    source_page_url: str,
    url_reason: str | None,
    text_reason: str | None,
) -> int:
    rank = 0
    lower_url = candidate_url.lower()
    if "/id" in lower_url:
        rank += 100
    if url_reason:
        rank += 40
    if text_reason:
        rank += 20
    rank += len(lower_url.split("/"))
    if source_page_url != candidate_url:
        rank += 5
    return rank


def is_obvious_category_page(final_url: str, title: str, normalized_text: str) -> bool:
    lower_url = final_url.lower()
    lower_title = title.lower()
    if re.search(r"/id\d+/?$", lower_url) or "boat id:" in normalized_text:
        return False
    category_markers = [
        "/boats-for-sale/",
        "/nautika",
        "/plovila",
        "/oglasnik",
        "/mali_oglasi/",
        "/search",
        "/pretraga",
        "/broker",
    ]
    generic_title_markers = [
        "boats for sale",
        "nautika",
        "plovila",
        "broker directory",
        "search",
        "burza nautike",
        "portal",
    ]
    if any(marker in lower_title for marker in generic_title_markers):
        return True
    if any(marker in lower_url for marker in category_markers) and "code-" not in lower_url and "/oglas/" not in lower_url:
        if normalized_text.count("boats for sale") > 1 or normalized_text.count("broker directory") > 0:
            return True
    return False


def is_render_shell_response(response: HttpResponse) -> bool:
    if response.status_code != 200 or not response.body:
        return False

    normalized_text = normalize_text(response.body)
    lowered_body = response.body.lower()
    title = extract_title(response.body).lower()
    if "captcha" in title or "shieldsquare" in normalized_text:
        return False
    return bool(
        "__next" in lowered_body
        or "__nuxt" in lowered_body
        or "application/ld+json" in lowered_body
        or len(normalized_text) < 400
    )


def normalize_text(raw_html: str) -> str:
    return " ".join(html.unescape(strip_tags(raw_html)).lower().split())


def summarize_detail_discovery_rows(results: list[SourceResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        if not result.detail_discovery_attempted:
            continue
        for item in result.detail_discovery_results:
            rows.append(
                {
                    "source_id": result.source_id,
                    "source_name": item.source_name,
                    "classification": result.classification,
                    "source_page_url": item.source_page_url,
                    "candidate_detail_url": item.candidate_detail_url,
                    "link_text_sample": item.link_text_sample,
                    "url_pattern_reason": item.url_pattern_reason,
                    "http_status": item.http_status,
                    "final_url": item.final_url,
                    "is_probable_detail_page": item.is_probable_detail_page,
                    "rejection_reason": item.rejection_reason or "",
                }
            )
    return rows
