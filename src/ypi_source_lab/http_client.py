from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass


DEFAULT_USER_AGENT = (
    "YPI-Research-SourceProbe/0.1 "
    "(public-source suitability testing; contact: ypi-research@example.com)"
)


@dataclass
class HttpResponse:
    url: str
    final_url: str
    status_code: int | None
    headers: dict[str, str]
    body: str
    error: str | None = None


class PoliteHttpClient:
    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 20.0,
        min_delay_seconds: float = 2.0,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.min_delay_seconds = min_delay_seconds
        self._last_request_started_at = 0.0

    def get(self, url: str, max_bytes: int = 131_072) -> HttpResponse:
        self._sleep_if_needed()
        self._last_request_started_at = time.monotonic()

        request = urllib.request.Request(
            url=url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xml,text/plain;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body_bytes = response.read(max_bytes)
                return HttpResponse(
                    url=url,
                    final_url=response.geturl(),
                    status_code=getattr(response, "status", None),
                    headers=dict(response.headers.items()),
                    body=body_bytes.decode("utf-8", errors="replace"),
                    error=None,
                )
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read(min(max_bytes, 32_768))
            return HttpResponse(
                url=url,
                final_url=exc.geturl(),
                status_code=exc.code,
                headers=dict(exc.headers.items()),
                body=body_bytes.decode("utf-8", errors="replace"),
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - keep probe resilient
            return HttpResponse(
                url=url,
                final_url=url,
                status_code=None,
                headers={},
                body="",
                error=f"{type(exc).__name__}: {exc}",
            )

    def _sleep_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_started_at
        remaining = self.min_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
