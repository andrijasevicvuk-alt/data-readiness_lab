from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.croatia-yachting.hr/en"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/yachts-for-sale",
        f"{base_url}/yachts-for-sale/used-boats",
    ]
    return probe_source(
        source_id="croatian_yachting",
        source_name="Croatian Yachting",
        base_url=base_url,
        target_confidence="official_public_url",
        target_source_note="Targets were corrected from live public navigation on Croatia Yachting's website.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/yachts-for-sale/used-boats",
            preferred_anchor_texts=["Boat details"],
            detail_url_must_contain=["/yachts-for-sale/", "/used-boats/"],
            detail_url_deny_contain=["/yachts-for-sale/used-boats", "/yachts-for-sale?page", "/contact"],
            brand_keywords=[
                "Hanse",
                "Bali",
                "Dehler",
                "Sealine",
                "Fjord",
                "Ryck",
                "Austin Parker",
                "Lagoon",
                "Bellini",
                "SPX",
            ],
            location_keywords=["Split", "Kastela", "Dubrovnik", "Biograd", "Marina", "Croatia"],
            max_detail_pages=3,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Using the public English-language sales pages exposed in the site's own navigation.",
        ],
    )
