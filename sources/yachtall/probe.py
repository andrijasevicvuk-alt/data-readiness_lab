from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.models import FieldProbeConfig
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.yachtall.com/en"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/boats-for-sale",
        f"{base_url}/used-boats",
    ]
    return probe_source(
        source_id="yachtall",
        source_name="Yachtall",
        base_url=base_url,
        target_confidence="search_discovered_public_url",
        target_source_note="Using the public Yachtall domain with small-scope public listing entry points.",
        field_probe_config=FieldProbeConfig(
            homepage_url=f"{base_url}/",
            listing_page_url=f"{base_url}/used-boats",
            preferred_anchor_texts=["details", "more"],
            detail_url_must_contain=["boat", "yacht"],
            detail_url_deny_contain=["used-boats", "boats-for-sale", "search"],
            brand_keywords=["Beneteau", "Jeanneau", "Lagoon", "Bavaria", "Hanse"],
            location_keywords=["Croatia", "Split", "Trogir", "Marina", "Europe"],
            max_detail_pages=1,
        ),
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Wave 1 source probe with a small public-page sample only.",
        ],
    )
