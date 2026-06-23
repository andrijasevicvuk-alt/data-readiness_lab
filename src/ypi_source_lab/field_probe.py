from __future__ import annotations

import html
import re
import urllib.parse
from html.parser import HTMLParser

from .http_client import HttpResponse, PoliteHttpClient
from .models import FieldProbeConfig, FieldProbePageResult, SourceResult


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        self._current_href = attrs_dict.get("href")
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        self.links.append(
            {
                "href": self._current_href,
                "text": " ".join(part.strip() for part in self._text_parts if part.strip()),
            }
        )
        self._current_href = None
        self._text_parts = []


def run_field_probe(
    *,
    client: PoliteHttpClient,
    source_result: SourceResult,
    config: FieldProbeConfig,
) -> None:
    source_result.field_probe_attempted = True

    homepage_response = client.get(config.homepage_url, max_bytes=350_000)
    listing_response = client.get(config.listing_page_url, max_bytes=350_000)

    page_results = [
        build_field_page_result(
            page_type="homepage",
            response=homepage_response,
            config=config,
        ),
        build_field_page_result(
            page_type="listing",
            response=listing_response,
            config=config,
        ),
    ]

    discovered_urls = discover_detail_urls(listing_response.body, config)
    if not discovered_urls:
        source_result.field_probe_notes.append(
            "No listing detail URLs were confirmed from raw listing-page HTML."
        )

    for detail_url in discovered_urls[: config.max_detail_pages]:
        response = client.get(detail_url, max_bytes=350_000)
        page_results.append(
            build_field_page_result(
                page_type="detail",
                response=response,
                config=config,
            )
        )

    source_result.field_probe_page_results = page_results
    detail_pages = [item for item in page_results if item.page_type == "detail"]
    source_result.listing_pages_tested = len(detail_pages)
    source_result.price_signal_visible = any(item.asking_price_signal_visible for item in detail_pages)
    source_result.year_signal_visible = any(item.year_signal_visible for item in detail_pages)
    source_result.location_signal_visible = any(item.location_signal_visible for item in detail_pages)
    source_result.engine_signal_visible = any(item.engine_signal_visible for item in detail_pages)
    source_result.stable_listing_url_visible = any(item.stable_listing_url_visible for item in detail_pages)
    source_result.raw_html_contains_structured_data = any(
        item.raw_html_contains_structured_data for item in page_results
    )

    if detail_pages:
        source_result.field_probe_notes.append(
            f"Discovered and tested {len(detail_pages)} public detail page(s) from the listing page."
        )

    source_result.classification = classify_field_probe(source_result)


def build_field_page_result(
    *,
    page_type: str,
    response: HttpResponse,
    config: FieldProbeConfig,
) -> FieldProbePageResult:
    body = response.body or ""
    normalized_text = " ".join(strip_tags(body).split())
    raw_search_text = body.replace("\\/", "/")
    combined_text = f"{normalized_text} {raw_search_text}"
    lower_combined_text = combined_text.lower()
    title_text = extract_title(body)
    title_visible = bool(title_text)
    image_count = len(re.findall(r"<img\b", body, flags=re.IGNORECASE))

    price_visible = bool(
        re.search(r"(\u20ac|\bEUR\b|\$|\bUSD\b|\bGBP\b)\s*[0-9][0-9., ]+", combined_text)
        or re.search(r'"price"\s*:\s*"?(?:[0-9][0-9., ]+)"?', raw_search_text, flags=re.IGNORECASE)
    )
    currency_visible = bool(
        re.search(r"(\u20ac|\bEUR\b|\$|\bUSD\b|\bGBP\b)", combined_text)
        or re.search(r'priceCurrency"\s*:\s*"?(EUR|USD|GBP)"?', raw_search_text, flags=re.IGNORECASE)
    )
    brand_visible = has_brand_signal(combined_text, config.brand_keywords)
    model_visible = has_model_signal(combined_text, config.brand_keywords)
    year_visible = bool(re.search(r"\b(19|20)\d{2}\b", combined_text))
    location_visible = has_location_signal(lower_combined_text, config.location_keywords)
    engine_visible = bool(
        re.search(r"\b(engine|engines|hp|kw|yanmar|volvo|mercury|honda|diesel)\b", lower_combined_text)
    )
    length_visible = bool(
        re.search(r"\b(loa|length)\b", lower_combined_text)
        or re.search(r"\b\d{1,2}(?:[.,]\d{1,2})?\s?(m|ft)\b", combined_text)
    )
    stable_url_visible = page_type == "detail" and is_stable_listing_url(response.url)
    stable_id_visible = bool(
        re.search(r"\bcode\s*[\(-]?\s*[0-9]{2,}\)?", lower_combined_text)
        or re.search(r"\blisting id\b\s*[:# -]*[A-Za-z0-9-]{2,}", lower_combined_text)
        or re.search(r'data-[a-z-]*id="listing', body, flags=re.IGNORECASE)
    )
    structured_visible = bool(
        re.search(r"application/ld\+json|schema\.org|\"@type\"|__NEXT_DATA__|__NUXT__", body, flags=re.IGNORECASE)
    )

    notes: list[str] = []
    if response.status_code != 200:
        notes.append("Page did not return HTTP 200 during field probe.")
    if page_type == "listing" and image_count == 0:
        notes.append("No obvious listing images were visible in raw HTML.")
    if page_type == "detail" and not stable_url_visible:
        notes.append("Detail page URL did not look like a clearly stable listing URL.")

    return FieldProbePageResult(
        page_type=page_type,
        url=response.url,
        status_code=response.status_code,
        title_signal_visible=title_visible,
        asking_price_signal_visible=price_visible,
        currency_signal_visible=currency_visible,
        builder_brand_signal_visible=brand_visible,
        model_signal_visible=model_visible,
        year_signal_visible=year_visible,
        location_signal_visible=location_visible,
        engine_signal_visible=engine_visible,
        length_signal_visible=length_visible,
        stable_listing_url_visible=stable_url_visible,
        stable_listing_id_signal_visible=stable_id_visible,
        image_presence_visible=image_count > 0 or "og:image" in body.lower(),
        image_count_estimate=image_count,
        raw_html_contains_structured_data=structured_visible,
        notes=notes,
    )


def discover_detail_urls(listing_html: str, config: FieldProbeConfig) -> list[str]:
    if not listing_html:
        return []

    parser = LinkExtractor()
    parser.feed(listing_html)

    preferred_texts = [item.lower() for item in config.preferred_anchor_texts]
    accepted: list[str] = []
    seen: set[str] = set()

    for link in parser.links:
        href = link.get("href", "").strip()
        text = link.get("text", "").strip().lower()
        absolute_url = normalize_url(config.listing_page_url, href)
        if not absolute_url:
            continue
        if not is_same_origin(config.listing_page_url, absolute_url):
            continue
        if absolute_url in {
            strip_trailing_slash(config.homepage_url),
            strip_trailing_slash(config.listing_page_url),
        }:
            continue
        if any(fragment.lower() in absolute_url.lower() for fragment in config.detail_url_deny_contain):
            continue

        has_text_match = any(candidate in text for candidate in preferred_texts)
        has_url_match = any(candidate.lower() in absolute_url.lower() for candidate in config.detail_url_must_contain)
        if not has_text_match and not has_url_match:
            continue

        cleaned_url = strip_fragment(absolute_url)
        if cleaned_url not in seen:
            seen.add(cleaned_url)
            accepted.append(cleaned_url)

    if accepted:
        return accepted

    for absolute_url in discover_urls_from_structured_data(listing_html):
        if not is_same_origin(config.listing_page_url, absolute_url):
            continue
        if any(fragment.lower() in absolute_url.lower() for fragment in config.detail_url_deny_contain):
            continue
        if config.detail_url_must_contain and not any(
            candidate.lower() in absolute_url.lower() for candidate in config.detail_url_must_contain
        ):
            continue
        cleaned_url = strip_fragment(absolute_url)
        if cleaned_url not in seen:
            seen.add(cleaned_url)
            accepted.append(cleaned_url)

    return accepted


def classify_field_probe(source_result: SourceResult) -> str:
    detail_pages = [
        item for item in source_result.field_probe_page_results if item.page_type == "detail" and item.status_code == 200
    ]
    if not detail_pages:
        listing_page = next(
            (item for item in source_result.field_probe_page_results if item.page_type == "listing"),
            None,
        )
        if listing_page and listing_page.raw_html_contains_structured_data and not listing_page.image_presence_visible:
            return "candidate_accessible_needs_browser_rendering"
        return "candidate_accessible_listing_discovery_unclear"

    richest_detail = max(
        detail_pages,
        key=lambda item: sum(
            [
                item.title_signal_visible,
                item.asking_price_signal_visible,
                item.currency_signal_visible,
                item.builder_brand_signal_visible,
                item.model_signal_visible,
                item.year_signal_visible,
                item.location_signal_visible,
                item.engine_signal_visible,
                item.length_signal_visible,
                item.stable_listing_url_visible,
                item.image_presence_visible,
            ]
        ),
    )

    visible_count = sum(
        [
            richest_detail.title_signal_visible,
            richest_detail.asking_price_signal_visible,
            richest_detail.currency_signal_visible,
            richest_detail.builder_brand_signal_visible,
            richest_detail.model_signal_visible,
            richest_detail.year_signal_visible,
            richest_detail.location_signal_visible,
            richest_detail.engine_signal_visible,
            richest_detail.length_signal_visible,
            richest_detail.stable_listing_url_visible,
            richest_detail.image_presence_visible,
        ]
    )

    if (
        visible_count >= 7
        and richest_detail.asking_price_signal_visible
        and richest_detail.length_signal_visible
        and richest_detail.stable_listing_url_visible
    ):
        return "candidate_accessible_fields_visible"
    if visible_count <= 3 and any(
        item.raw_html_contains_structured_data for item in source_result.field_probe_page_results
    ):
        return "candidate_accessible_needs_browser_rendering"
    return "candidate_accessible_fields_weak"


def extract_title(body: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(strip_tags(match.group(1))).strip() if match else ""


def strip_tags(raw_html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def has_brand_signal(text: str, brand_keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in brand_keywords) or bool(
        re.search(r"\b(builder|brand|shipyard|manufacturer)\b", lowered)
    )


def has_model_signal(text: str, brand_keywords: list[str]) -> bool:
    for keyword in brand_keywords:
        pattern = re.compile(rf"\b{re.escape(keyword)}\s+[A-Za-z0-9][A-Za-z0-9 ./-]{{1,30}}", flags=re.IGNORECASE)
        if pattern.search(text):
            return True
    return bool(re.search(r"\bmodel\b", text, flags=re.IGNORECASE))


def has_location_signal(lower_text: str, location_keywords: list[str]) -> bool:
    return any(keyword.lower() in lower_text for keyword in location_keywords) or bool(
        re.search(r"\b(location|marina|croatia|split|trogir|dubrovnik|kastela|biograd)\b", lower_text)
    )


def normalize_url(base_url: str, href: str) -> str | None:
    if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
        return None
    return urllib.parse.urljoin(base_url, href)


def discover_urls_from_structured_data(raw_html: str) -> list[str]:
    discovered: list[str] = []
    seen: set[str] = set()
    patterns = [
        r'"url"\s*:\s*"((?:https?:)?\\?/\\?/[^"]+)"',
        r'"item"\s*:\s*"((?:https?:)?\\?/\\?/[^"]+)"',
    ]
    for pattern in patterns:
        for match in re.findall(pattern, raw_html, flags=re.IGNORECASE):
            cleaned = match.replace("\\/", "/")
            if cleaned.startswith("//"):
                cleaned = "https:" + cleaned
            if cleaned.startswith("http") and cleaned not in seen:
                seen.add(cleaned)
                discovered.append(cleaned)
    return discovered


def strip_fragment(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def strip_trailing_slash(url: str) -> str:
    return url[:-1] if url.endswith("/") else url


def is_same_origin(base_url: str, other_url: str) -> bool:
    base = urllib.parse.urlsplit(base_url)
    other = urllib.parse.urlsplit(other_url)
    return base.scheme == other.scheme and base.netloc == other.netloc


def is_stable_listing_url(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    path = parts.path.strip("/")
    return bool(path and len(path.split("/")) >= 2)


def summarize_field_probe_rows(results: list[SourceResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        if not result.field_probe_attempted:
            continue
        for page in result.field_probe_page_results:
            rows.append(
                {
                    "source_id": result.source_id,
                    "source_name": result.source_name,
                    "classification": result.classification,
                    "page_type": page.page_type,
                    "url": page.url,
                    "status_code": page.status_code,
                    "title_signal_visible": page.title_signal_visible,
                    "asking_price_signal_visible": page.asking_price_signal_visible,
                    "currency_signal_visible": page.currency_signal_visible,
                    "builder_brand_signal_visible": page.builder_brand_signal_visible,
                    "model_signal_visible": page.model_signal_visible,
                    "year_signal_visible": page.year_signal_visible,
                    "location_signal_visible": page.location_signal_visible,
                    "engine_signal_visible": page.engine_signal_visible,
                    "length_signal_visible": page.length_signal_visible,
                    "stable_listing_url_visible": page.stable_listing_url_visible,
                    "stable_listing_id_signal_visible": page.stable_listing_id_signal_visible,
                    "image_presence_visible": page.image_presence_visible,
                    "image_count_estimate": page.image_count_estimate,
                    "raw_html_contains_structured_data": page.raw_html_contains_structured_data,
                    "notes": " | ".join(page.notes),
                }
            )
    return rows
