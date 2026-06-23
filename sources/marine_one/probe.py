from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.yachtbrokerage.eu"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/boats-for-sale",
    ]
    return probe_source(
        source_id="marine_one",
        source_name="Marine One",
        base_url=base_url,
        target_confidence="official_public_url",
        target_source_note="Marine One branding is present on the public YachtBrokerage website, which exposes a boats-for-sale page.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/boats-for-sale",
            preferred_anchor_texts=["Details", "Details..", "Check out"],
            detail_url_must_contain=["/boat-details", "/boats-for-sale/", "/marine-one-brokerage/"],
            detail_url_deny_contain=["/boats-for-sale?page", "/boats-for-sale?"],
            brand_keywords=[
                "Bali",
                "Lagoon",
                "Beneteau",
                "Jeanneau",
                "Hanse",
                "Bavaria",
                "Fountaine Pajot",
                "Maiora",
                "Nuva",
                "Hobby",
            ],
            location_keywords=["Croatia", "Europe", "Trogir", "Marina", "Split"],
            max_detail_pages=3,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Replaced the earlier failing guessed domain with the active public YachtBrokerage site carrying Marine One branding.",
        ],
    )
