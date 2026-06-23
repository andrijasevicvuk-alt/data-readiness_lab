from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PageProbeResult:
    url: str
    status_code: int | None
    outcome: str
    reason: str


@dataclass
class FieldProbeConfig:
    homepage_url: str
    listing_page_url: str
    preferred_anchor_texts: list[str] = field(default_factory=list)
    detail_url_must_contain: list[str] = field(default_factory=list)
    detail_url_deny_contain: list[str] = field(default_factory=list)
    brand_keywords: list[str] = field(default_factory=list)
    location_keywords: list[str] = field(default_factory=list)
    max_detail_pages: int = 3


@dataclass
class FieldProbePageResult:
    page_type: str
    url: str
    status_code: int | None
    title_signal_visible: bool
    asking_price_signal_visible: bool
    currency_signal_visible: bool
    builder_brand_signal_visible: bool
    model_signal_visible: bool
    year_signal_visible: bool
    location_signal_visible: bool
    engine_signal_visible: bool
    length_signal_visible: bool
    stable_listing_url_visible: bool
    stable_listing_id_signal_visible: bool
    image_presence_visible: bool
    image_count_estimate: int
    raw_html_contains_structured_data: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class DetailDiscoveryConfig:
    homepage_url: str
    discovery_page_url: str
    preferred_anchor_texts: list[str] = field(default_factory=list)
    detail_url_must_contain: list[str] = field(default_factory=list)
    detail_url_deny_contain: list[str] = field(default_factory=list)
    max_candidate_links: int = 5


@dataclass
class DetailDiscoveryCandidateResult:
    source_name: str
    source_page_url: str
    candidate_detail_url: str
    link_text_sample: str
    url_pattern_reason: str
    http_status: int | None
    final_url: str
    is_probable_detail_page: bool
    rejection_reason: str | None = None


@dataclass
class SourceResult:
    source_id: str
    source_name: str
    base_url: str
    target_confidence: str
    target_source_note: str
    classification: str
    robots_txt_url: str
    robots_txt_status_code: int | None
    robots_txt_accessible: bool
    robots_allows_probe_targets: bool | None
    sitemap_xml_url: str
    sitemap_xml_status_code: int | None
    sitemap_xml_accessible: bool
    field_probe_attempted: bool = False
    listing_pages_tested: int = 0
    price_signal_visible: bool = False
    year_signal_visible: bool = False
    location_signal_visible: bool = False
    engine_signal_visible: bool = False
    stable_listing_url_visible: bool = False
    raw_html_contains_structured_data: bool = False
    field_probe_notes: list[str] = field(default_factory=list)
    field_probe_page_results: list[FieldProbePageResult] = field(default_factory=list)
    detail_discovery_attempted: bool = False
    probable_detail_pages_found: int = 0
    detail_discovery_notes: list[str] = field(default_factory=list)
    detail_discovery_results: list[DetailDiscoveryCandidateResult] = field(default_factory=list)
    page_results: list[PageProbeResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
