from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import DetailDiscoveryConfig, FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.theyachtmarket.com/en"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/boats-for-sale/",
        f"{base_url}/boats-for-sale/croatia/",
    ]
    return probe_source(
        source_id="theyachtmarket",
        source_name="TheYachtMarket",
        base_url=base_url,
        target_confidence="official_public_url",
        target_source_note="Using TheYachtMarket public English-language domain and obvious sale pages.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/boats-for-sale/",
            preferred_anchor_texts=["view", "details"],
            detail_url_must_contain=["/boats-for-sale/", "/boat/"],
            detail_url_deny_contain=["/boats-for-sale/", "/search", "/brokers"],
            brand_keywords=["Beneteau", "Jeanneau", "Bavaria", "Lagoon", "Princess"],
            location_keywords=["Croatia", "Split", "Trogir", "Marina", "Europe"],
            max_detail_pages=1,
        ),
        detail_discovery_config=DetailDiscoveryConfig(
            homepage_url=f"{base_url}/",
            discovery_page_url=f"{base_url}/boats-for-sale/croatia/",
            preferred_anchor_texts=["view", "details"],
            detail_url_must_contain=["/id", "/boats-for-sale/"],
            detail_url_deny_contain=["/search", "/brokers", "/charter", "/news", "/contact"],
            max_candidate_links=5,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 1 source probe with one safe detail page at most.",
        ],
    )
