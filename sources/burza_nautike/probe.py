from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import DetailDiscoveryConfig, FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.burzanautike.com"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/plovila",
        f"{base_url}/oglasnik",
    ]
    return probe_source(
        source_id="burza_nautike",
        source_name="Burza Nautike",
        base_url=base_url,
        target_confidence="search_discovered_public_url",
        target_source_note="Using the public Burza Nautike domain with obvious nautical/classified entry paths.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/plovila",
            preferred_anchor_texts=["detalji", "više", "oglas"],
            detail_url_must_contain=["/oglas/", "/plovila/"],
            detail_url_deny_contain=["/plovila", "/oglasnik", "/pretraga"],
            brand_keywords=["Jeanneau", "Beneteau", "Bavaria", "Mercury", "Yamaha"],
            location_keywords=["Croatia", "Split", "Zadar", "Šibenik", "Rijeka"],
            max_detail_pages=1,
        ),
        detail_discovery_config=DetailDiscoveryConfig(
            homepage_url=f"{base_url}/",
            discovery_page_url=f"{base_url}/plovila",
            preferred_anchor_texts=["detalji", "više", "oglas"],
            detail_url_must_contain=["/mali_oglasi/", "/oglas/"],
            detail_url_deny_contain=["/plovila", "/oglasnik", "/pretraga", "/login", "/predaja/"],
            max_candidate_links=5,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 1 source probe uses only a tiny public sample.",
        ],
    )
