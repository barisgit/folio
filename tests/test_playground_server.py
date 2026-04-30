"""Tests for the Folio playground HTTP server."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from folio.core.cache import cache_build, cache_paths
from folio.services.playground_server import (
    PlaygroundHTTPServer,
    _PlaygroundRequestHandler,
    create_playground_server,
    playground_url,
)
from folio.services.tweaks_load import load_spec_with_tweaks


SPEC_WITH_TWEAKS = dedent(
    """
    from folio.dsl import TextStyle, collection, document, page, text, tweaks

    theme = tweaks.group(
        "theme",
        primary=tweaks.color(default="#d9a64b"),
        hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
    )

    HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)


    def build():
        return collection(
            document(
                "demo",
                pages=[
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[text("hero", 10, 20, "Hi", style=HERO)],
                    )
                ],
            )
        )
    """
).strip() + "\n"


SPEC_WITHOUT_TWEAKS = dedent(
    """
    from folio.dsl import collection, document, page, text


    def build():
        return collection(
            document(
                "demo",
                pages=[
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[text("hero", 10, 20, "Hi", size_pt=12)],
                    )
                ],
            )
        )
    """
).strip() + "\n"


@contextmanager
def _running_server(spec_path: Path, *, host: str = "127.0.0.1") -> Iterator[str]:
    server = create_playground_server(spec_path, host=host, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield playground_url(server)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _write_spec(tmp_path: Path, body: str = SPEC_WITH_TWEAKS) -> Path:
    spec_path = tmp_path / "build.py"
    spec_path.write_text(body, encoding="utf-8")
    return spec_path


def _json_get(url: str) -> dict[str, object]:
    with urlopen(url, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def _json_patch(url: str, payload: dict[str, object]) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method="PATCH",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def test_create_playground_server_binds_configurable_host_and_ephemeral_port(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    server = create_playground_server(spec_path, host="127.0.0.1", port=0)
    try:
        assert isinstance(server, PlaygroundHTTPServer)
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] > 0
        assert playground_url(server).startswith("http://127.0.0.1:")
    finally:
        server.server_close()


def test_get_root_returns_html_shell(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        with urlopen(base_url, timeout=5) as response:
            body = response.read().decode("utf-8")

    assert response.status == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "Folio Tweaks Playground" in body
    assert "/api/state" in body


def test_get_root_includes_playground_ui_hooks(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        with urlopen(base_url, timeout=5) as response:
            body = response.read().decode("utf-8")

    assert 'id="page-selector"' in body
    assert 'id="preview-container"' in body
    assert 'id="preview-frame"' in body
    assert 'id="tweak-panel"' in body
    assert 'id="diagnostics"' in body
    assert "renderPageSelector" in body
    assert "renderControls" in body
    assert "renderPreview" in body


def test_get_root_ui_applies_live_vars_and_debounces_persistence(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        with urlopen(base_url, timeout=5) as response:
            body = response.read().decode("utf-8")

    assert "style.setProperty(tweak.cssVar, liveCssValue" in body
    assert "if (tweak.kind === 'size_pt' || tweak.kind === 'letter_spacing') return `${value}pt`;" in body
    assert "const DEBOUNCE_MS" in body
    assert "setTimeout(() => patchTweak" in body
    assert "clearTimeout(pendingTimers.get" in body
    assert "fetch(API_TWEAKS" in body
    assert "JSON.stringify({ key: tweak.key" in body


def test_get_root_ui_renders_controls_and_diagnostics(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        with urlopen(base_url, timeout=5) as response:
            body = response.read().decode("utf-8")

    assert "if (tweak.kind === 'color') return 'color';" in body
    assert "input.type = controlInputType(tweak)" in body
    assert "range.type = 'range'" in body
    assert "document.createElement('select')" in body
    assert "displayDiagnostics" in body
    assert "control-diagnostic" in body
    assert "is-invalid" in body


def test_get_api_state_returns_pages_tweaks_values_and_diagnostics(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    (tmp_path / "theme.toml").write_text('[theme]\nprimary = "#445566"\n', encoding="utf-8")

    with _running_server(spec_path) as base_url:
        state = _json_get(base_url + "api/state")

    assert state["specPath"] == str(spec_path.resolve())
    assert state["valuesPath"] == str(tmp_path / "theme.toml")
    assert state["values"]["theme.primary"] == "#445566"  # type: ignore[index]
    assert state["diagnostics"] == []
    assert state["pages"][0]["filename"] == "one.svg"  # type: ignore[index]
    assert "var(--folio-tweak-theme-primary, #445566)" in state["pages"][0]["svg"]  # type: ignore[index]
    assert state["tweaks"][0]["key"] == "theme.primary"  # type: ignore[index]
    assert state["tweaks"][0]["cssVar"] == "--folio-tweak-theme-primary"  # type: ignore[index]


def test_get_api_state_no_tweaks_empty_state(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, SPEC_WITHOUT_TWEAKS)

    with _running_server(spec_path) as base_url:
        state = _json_get(base_url + "api/state")

    assert len(state["pages"]) == 1  # type: ignore[arg-type]
    assert state["tweaks"] == []
    assert state["values"] == {}
    assert state["diagnostics"] == []


def test_patch_api_tweaks_valid_edit_writes_theme_toml_and_returns_state(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        state = _json_patch(
            base_url + "api/tweaks",
            {"key": "theme.primary", "value": "#ff3366"},
        )

    assert state["values"]["theme.primary"] == "#ff3366"  # type: ignore[index]
    assert 'primary = "#ff3366"' in (tmp_path / "theme.toml").read_text(encoding="utf-8")
    assert "var(--folio-tweak-theme-primary, #ff3366)" in state["pages"][0]["svg"]  # type: ignore[index]


def test_patch_api_tweaks_accepts_updates_object(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        state = _json_patch(
            base_url + "api/tweaks",
            {"updates": {"theme.hero_size_pt": 70}},
        )

    assert state["values"]["theme.hero_size_pt"] == 70.0  # type: ignore[index]
    assert "hero_size_pt = 70.0" in (tmp_path / "theme.toml").read_text(encoding="utf-8")


def test_create_playground_server_fails_before_serving_invalid_spec(tmp_path: Path) -> None:
    spec_path = _write_spec(
        tmp_path,
        "from folio.dsl import collection\n\n\ndef build():\n    raise RuntimeError('boom')\n",
    )

    try:
        create_playground_server(spec_path, host="127.0.0.1", port=0)
    except RuntimeError as exc:
        assert "boom" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected startup failure")


def test_patch_api_tweaks_rebuild_edit_returns_rerendered_preview(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        state = _json_patch(
            base_url + "api/tweaks",
            {"key": "theme.hero_size_pt", "value": 70},
        )

    assert state["values"]["theme.hero_size_pt"] == 70.0  # type: ignore[index]
    assert 'font-size="var(--folio-tweak-theme-hero-size-pt, 70.0pt)"' in state["pages"][0]["svg"]  # type: ignore[index]


def test_patch_api_tweaks_debounces_concurrent_updates(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    _json_patch,
                    base_url + "api/tweaks",
                    {"key": "theme.primary", "value": "#ff3366"},
                ),
                executor.submit(
                    _json_patch,
                    base_url + "api/tweaks",
                    {"key": "theme.hero_size_pt", "value": 70},
                ),
            ]
            states = [future.result(timeout=5) for future in futures]

    assert {state["values"]["theme.primary"] for state in states} == {"#ff3366"}  # type: ignore[index]
    assert {state["values"]["theme.hero_size_pt"] for state in states} == {70.0}  # type: ignore[index]
    written = (tmp_path / "theme.toml").read_text(encoding="utf-8")
    assert 'primary = "#ff3366"' in written
    assert "hero_size_pt = 70.0" in written


def test_patch_api_tweaks_rereads_external_edit_before_write(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    values_path = tmp_path / "theme.toml"
    values_path.write_text('[theme]\nprimary = "#111111"\nhero_size_pt = 60\n', encoding="utf-8")

    with _running_server(spec_path) as base_url:
        values_path.write_text('[theme]\nprimary = "#222222"\nhero_size_pt = 68\n', encoding="utf-8")
        state = _json_patch(
            base_url + "api/tweaks",
            {"key": "theme.primary", "value": "#abcdef"},
        )

    written = values_path.read_text(encoding="utf-8")
    assert state["values"]["theme.primary"] == "#abcdef"  # type: ignore[index]
    assert state["values"]["theme.hero_size_pt"] == 68.0  # type: ignore[index]
    assert 'primary = "#abcdef"' in written
    assert "hero_size_pt = 68.0" in written


def test_playground_server_api_does_not_modify_last_build_cache(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    build_outcome = load_spec_with_tweaks(spec_path.resolve())
    cached = cache_build(build_outcome.result, spec_path=spec_path.resolve())
    before_manifest = cached.manifest.read_text(encoding="utf-8")
    before_page = cached.page_map[1].read_text(encoding="utf-8")

    with _running_server(spec_path) as base_url:
        _json_get(base_url + "api/state")
        _json_patch(base_url + "api/tweaks", {"key": "theme.primary", "value": "#ff3366"})

    assert cache_paths(spec_path.resolve()).root.exists()
    assert cached.manifest.read_text(encoding="utf-8") == before_manifest
    assert cached.page_map[1].read_text(encoding="utf-8") == before_page


def test_patch_api_tweaks_invalid_edit_returns_400_and_preserves_file(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)
    values_path = tmp_path / "theme.toml"
    values_path.write_text('[theme]\nprimary = "#445566"\nhero_size_pt = 64\n', encoding="utf-8")
    before = values_path.read_text(encoding="utf-8")

    with _running_server(spec_path) as base_url:
        request = Request(
            base_url + "api/tweaks",
            data=json.dumps({"key": "theme.hero_size_pt", "value": 120}).encode("utf-8"),
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        try:
            urlopen(request, timeout=5)
        except HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
        else:  # pragma: no cover - defensive
            raise AssertionError("expected HTTP 400")

    assert payload["diagnostics"][0]["key"] == "theme.hero_size_pt"
    assert values_path.read_text(encoding="utf-8") == before


def test_patch_api_tweaks_invalid_json_returns_400(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path)

    with _running_server(spec_path) as base_url:
        request = Request(
            base_url + "api/tweaks",
            data=b"not-json",
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        try:
            urlopen(request, timeout=5)
        except HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
        else:  # pragma: no cover - defensive
            raise AssertionError("expected HTTP 400")

    assert payload["diagnostics"][0]["severity"] == "error"


def test_send_body_ignores_client_disconnect() -> None:
    class BrokenWriter:
        def write(self, body: bytes) -> None:
            raise BrokenPipeError

    handler = object.__new__(_PlaygroundRequestHandler)
    handler.send_response = lambda status: None  # type: ignore[method-assign]
    handler.send_header = lambda name, value: None  # type: ignore[method-assign]
    handler.end_headers = lambda: None  # type: ignore[method-assign]
    handler.wfile = BrokenWriter()  # type: ignore[assignment]

    handler._send_body(HTTPStatus.OK, b"{}", content_type="application/json")
