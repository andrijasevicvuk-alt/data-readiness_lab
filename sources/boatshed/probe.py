from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import DetailDiscoveryConfig, FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source
from src.ypi_source_lab.wave2_probe import Wave2SourceConfig


def get_wave2_source_config() -> Wave2SourceConfig:
    base_url = "https://www.boatshed.com"
    return Wave2SourceConfig(
        source_id="boatshed",
        source_name="Boatshed",
        base_url=base_url,
        homepage_url=f"{base_url}/",
        listing_url=f"{base_url}/used-boats-for-sale.html",
        country_url_template="https://{slug}.boatshed.com/",
        target_source_note="Using Boatshed public network entry points and obvious country-subdomain brokerage pages where they exist.",
        preferred_anchor_texts=["details", "view boat", "more"],
        detail_url_must_contain=["boatshed.com/", "/boat/"],
        detail_url_deny_contain=["used-boats-for-sale", "/search", "/contact"],
        brand_keywords=["Beneteau", "Jeanneau", "Bavaria", "Lagoon", "Princess"],
        location_keywords=["Croatia", "Slovenia", "Italy", "Greece", "Turkey", "Montenegro", "Malta", "Spain", "France"],
        accessible_market_role="mediterranean_expansion_source",
    )


def run_probe(client: PoliteHttpClient):
    config = get_wave2_source_config()
    public_pages = [
        config.homepage_url,
        config.listing_url,
        config.country_url_template.format(slug="croatia", label="Croatia", query="Croatia"),
    ]
    return probe_source(
        source_id=config.source_id,
        source_name=config.source_name,
        base_url=config.base_url,
        target_confidence="search_discovered_public_url",
        target_source_note=config.target_source_note,
        field_probe_config=FieldProbeConfig(
            homepage_url=config.homepage_url,
            listing_page_url=config.listing_url,
            preferred_anchor_texts=config.preferred_anchor_texts,
            detail_url_must_contain=config.detail_url_must_contain,
            detail_url_deny_contain=config.detail_url_deny_contain,
            brand_keywords=config.brand_keywords,
            location_keywords=config.location_keywords,
            max_detail_pages=1,
        ),
        detail_discovery_config=DetailDiscoveryConfig(
            homepage_url=config.homepage_url,
            discovery_page_url=public_pages[-1],
            preferred_anchor_texts=config.preferred_anchor_texts,
            detail_url_must_contain=config.detail_url_must_contain,
            detail_url_deny_contain=config.detail_url_deny_contain,
            max_candidate_links=3,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 2 source added as a broker-network benchmark.",
        ],
    )
