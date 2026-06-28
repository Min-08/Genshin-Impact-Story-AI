from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


USER_AGENT = "project-amber-db-builder/0.6 (+local data builder)"


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    content_type: str | None
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self) -> Any:
        text = self.text
        if not text.strip():
            return None
        return json.loads(text)


def fetch_url(url: str, *, timeout: int = 60, retries: int = 3, sleep_seconds: float = 0.5) -> FetchResult:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                content_type = response.headers.get("Content-Type")
                body = response.read()
                return FetchResult(url=url, status=status, content_type=content_type, body=body)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt == retries:
                break
            time.sleep(sleep_seconds * attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def fetch_json(url: str, *, timeout: int = 60, retries: int = 3, sleep_seconds: float = 0.5) -> Any:
    return fetch_url(url, timeout=timeout, retries=retries, sleep_seconds=sleep_seconds).json()
