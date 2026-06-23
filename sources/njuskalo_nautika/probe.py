from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import DetailDiscoveryConfig, FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.njuskalo.hr"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/nautika",
        f"{base_url}/plovila",
    ]
    return probe_source(
        source_id="njuskalo_nautika",
        source_name="Njuškalo Nautika",
        base_url=base_url,
        target_confidence="official_public_url",
        target_source_note="Using public Njuškalo category pages for nautical listings.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/nautika",
            preferred_anchor_texts=["više", "detalji", "pogledaj"],
            detail_url_must_contain=["/oglas/", "/nautika/"],
            detail_url_deny_contain=["/nautika", "/plovila", "/trgovina"],
            brand_keywords=["Jeanneau", "Beneteau", "Bavaria", "Yamaha", "Mercury"],
            location_keywords=["Croatia", "Split", "Zadar", "Šibenik", "Rijeka"],
            max_detail_pages=1,
        ),
        detail_discovery_config=DetailDiscoveryConfig(
            homepage_url=f"{base_url}/",
            discovery_page_url=f"{base_url}/nautika",
            preferred_anchor_texts=["više", "detalji", "pogledaj", "oglas"],
            detail_url_must_contain=["/oglas/", "/nautika/"],
            detail_url_deny_contain=["/nautika", "/plovila", "/trgovina", "/help/"],
            max_candidate_links=5,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 1 source probe for a Croatia-focused classifieds source.",
        ],
    )
