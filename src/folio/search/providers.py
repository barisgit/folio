"""Stock-image search providers using stdlib HTTP only."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

Provider = Literal["openverse", "pexels", "pixabay"]
PROVIDERS: list[Provider] = ["openverse", "pexels", "pixabay"]
REQUEST_TIMEOUT_SECONDS = 20
STOCK_SEARCH_USER_AGENT = "Mozilla/5.0 folio-stock-search"


@dataclass(frozen=True)
class SearchResult:
    id: str
    provider: Provider
    description: str
    url: str
    thumbnail: str
    width: int
    height: int
    license: str = ""
    creator: str = ""
    source: str = ""


def _http_get_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Fetch JSON from *url* using stdlib :mod:`urllib`."""
    request_headers = {
        "User-Agent": STOCK_SEARCH_USER_AGENT,
        "Accept": "application/json",
        **(headers or {}),
    }
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_openverse(query: str, *, per_page: int = 10) -> list[SearchResult]:
    params = urllib.parse.urlencode({"q": query, "page_size": per_page})
    data = _http_get_json(f"https://api.openverse.org/v1/images/?{params}")
    return [
        SearchResult(
            id=str(r.get("id", "")),
            provider="openverse",
            description=r.get("title", ""),
            url=r.get("url", ""),
            thumbnail=r.get("thumbnail", ""),
            width=r.get("width", 0),
            height=r.get("height", 0),
            license=r.get("license", "") or "",
            creator=r.get("creator", "") or "",
            source=r.get("source", "") or "",
        )
        for r in data.get("results", [])
    ]


def _fetch_pexels(query: str, *, per_page: int = 10) -> list[SearchResult]:
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        raise RuntimeError("PEXELS_API_KEY environment variable is required for Pexels.")
    params = urllib.parse.urlencode({"query": query, "per_page": per_page})
    data = _http_get_json(
        f"https://api.pexels.com/v1/search?{params}",
        headers={"Authorization": api_key},
    )
    return [
        SearchResult(
            id=str(r.get("id", "")),
            provider="pexels",
            description=r.get("alt", "") or "",
            url=r.get("url", ""),
            thumbnail=r.get("src", {}).get("tiny", ""),
            width=r.get("width", 0),
            height=r.get("height", 0),
        )
        for r in data.get("photos", [])
    ]


def _fetch_pixabay(query: str, *, per_page: int = 10) -> list[SearchResult]:
    api_key = os.environ.get("PIXABAY_API_KEY", "")
    if not api_key:
        raise RuntimeError("PIXABAY_API_KEY environment variable is required for Pixabay.")
    params = urllib.parse.urlencode({"key": api_key, "q": query, "per_page": per_page})
    data = _http_get_json(f"https://pixabay.com/api/?{params}")
    return [
        SearchResult(
            id=str(r.get("id", "")),
            provider="pixabay",
            description=r.get("tags", ""),
            url=r.get("pageURL", ""),
            thumbnail=r.get("previewURL", ""),
            width=r.get("imageWidth", 0),
            height=r.get("imageHeight", 0),
        )
        for r in data.get("hits", [])
    ]


_FETCHERS: dict[Provider, object] = {
    "openverse": _fetch_openverse,
    "pexels": _fetch_pexels,
    "pixabay": _fetch_pixabay,
}


def fetch_stock(
    query: str,
    *,
    provider: Provider = "openverse",
    per_page: int = 10,
) -> list[SearchResult]:
    """Search stock images from the given provider."""
    fetcher = _FETCHERS[provider]
    return fetcher(query, per_page=per_page)  # type: ignore[operator]


def fetch_stock_multi(
    query: str,
    *,
    providers: list[Provider],
    per_page: int = 10,
) -> list[SearchResult]:
    """Search stock images from multiple providers, gracefully degrading on failure.

    Returns combined results from all successful providers.  Raises only when
    *every* provider fails.
    """
    all_results: list[SearchResult] = []
    errors: list[str] = []

    for prov in providers:
        try:
            fetcher = _FETCHERS[prov]
            all_results.extend(fetcher(query, per_page=per_page))  # type: ignore[operator]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{prov}: {exc}")

    if not all_results and errors:
        raise RuntimeError(
            "All providers failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return all_results
