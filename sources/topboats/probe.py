from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.topboats.com"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/en/boats-for-sale",
        f"{base_url}/en/boats-for-sale/croatia",
    ]
    return probe_source(
        source_id="topboats",
        source_name="TopBoats",
        base_url=base_url,
        target_confidence="search_discovered_public_url",
        target_source_note="Using the public TopBoats domain with obvious English sale paths.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/en/boats-for-sale",
            preferred_anchor_texts=["details", "view"],
            detail_url_must_contain=["boat", "boats-for-sale"],
            detail_url_deny_contain=["boats-for-sale/croatia", "boats-for-sale?", "/search"],
            brand_keywords=["Beneteau", "Jeanneau", "Bavaria", "Lagoon", "Azimut"],
            location_keywords=["Croatia", "Split", "Trogir", "Marina", "Europe"],
            max_detail_pages=1,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 1 source probe uses likely public English paths and should be refined only if public pages disagree.",
        ],
    )
