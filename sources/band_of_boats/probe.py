from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.bandofboats.com/en"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/boats-for-sale",
        f"{base_url}/used-boats-for-sale",
    ]
    return probe_source(
        source_id="band_of_boats",
        source_name="Band of Boats",
        base_url=base_url,
        target_confidence="official_public_url",
        target_source_note="Using the public Band of Boats English-language sale pages.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/used-boats-for-sale",
            preferred_anchor_texts=["see", "details", "view"],
            detail_url_must_contain=["/boat/", "/boats-for-sale/"],
            detail_url_deny_contain=["used-boats-for-sale", "boats-for-sale?"],
            brand_keywords=["Beneteau", "Jeanneau", "Lagoon", "Bavaria", "Fountaine Pajot"],
            location_keywords=["Croatia", "Split", "Trogir", "Marina", "Europe"],
            max_detail_pages=1,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 1 source probe uses public sale pages only.",
        ],
    )
