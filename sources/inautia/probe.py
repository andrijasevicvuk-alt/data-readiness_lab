from src.ypi_source_lab.http_client import PoliteHttpClient
from src.ypi_source_lab.probe_utils import probe_source


def run_probe(client: PoliteHttpClient):
    base_url = "https://www.inautia.com"
    public_pages = [
        f"{base_url}/",
        f"{base_url}/boats-for-sale/",
        f"{base_url}/used-boats/",
    ]
    return probe_source(
        source_id="inautia",
        source_name="iNautia",
        base_url=base_url,
        target_confidence="official_public_url",
        target_source_note="Using the public iNautia main domain for a minimal access check.",
        public_pages=public_pages,
        client=client,
        extra_notes=[
            "Probe is limited to a few public entry points on the assumed main domain.",
        ],
    )
