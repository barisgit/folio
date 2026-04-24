from __future__ import annotations

import json

from folio.services.search import providers


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_http_get_json_sends_user_agent_and_accept(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout: int):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["user_agent"] = request.get_header("User-agent")
        captured["accept"] = request.get_header("Accept")
        return _FakeResponse({"ok": True})

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)

    payload = providers._http_get_json("https://api.openverse.org/v1/images/?q=sunrise")

    assert payload == {"ok": True}
    assert captured == {
        "url": "https://api.openverse.org/v1/images/?q=sunrise",
        "timeout": providers.REQUEST_TIMEOUT_SECONDS,
        "user_agent": providers.STOCK_SEARCH_USER_AGENT,
        "accept": "application/json",
    }


def test_fetch_openverse_maps_results(monkeypatch) -> None:
    def fake_http_get_json(url: str, *, headers=None):
        assert "q=sunrise" in url
        assert "page_size=2" in url
        assert headers is None
        return {
            "results": [
                {
                    "id": "img-1",
                    "title": "Sunrise over hills",
                    "url": "https://example.com/full.jpg",
                    "thumbnail": "https://example.com/thumb.jpg",
                    "width": 1600,
                    "height": 900,
                    "license": "cc0",
                    "creator": "John Doe",
                    "source": "Wikimedia",
                }
            ]
        }

    monkeypatch.setattr(providers, "_http_get_json", fake_http_get_json)

    results = providers._fetch_openverse("sunrise", per_page=2)

    assert len(results) == 1
    assert results[0].provider == "openverse"
    assert results[0].id == "img-1"
    assert results[0].description == "Sunrise over hills"
    assert results[0].url == "https://example.com/full.jpg"
    assert results[0].thumbnail == "https://example.com/thumb.jpg"
    assert results[0].width == 1600
    assert results[0].height == 900
    assert results[0].license == "cc0"
    assert results[0].creator == "John Doe"
    assert results[0].source == "Wikimedia"
