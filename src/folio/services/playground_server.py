"""Stdlib HTTP server for the Folio tweak playground."""

from __future__ import annotations

import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from folio.services.playground import (
    PlaygroundState,
    PlaygroundUpdateError,
    apply_tweak_update,
    load_playground_state,
)

__all__ = [
    "PlaygroundHTTPServer",
    "create_playground_server",
    "playground_url",
    "serialize_playground_state",
]


class PlaygroundHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server bound to one Folio spec."""

    spec_path: Path
    startup_state: PlaygroundState


PLAYGROUND_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Folio Tweaks Playground</title>
</head>
<body>
  <main id=\"folio-playground\">
    <h1>Folio Tweaks Playground</h1>
    <p id=\"status\">Loading tweak state…</p>
    <section id=\"pages\" aria-label=\"Rendered pages\"></section>
    <section id=\"tweaks\" aria-label=\"Tweaks\"></section>
  </main>
  <script>
    fetch('/api/state')
      .then((response) => response.json())
      .then((state) => {
        document.getElementById('status').textContent =
          state.tweaks.length ? `${state.tweaks.length} tweak(s) loaded.` : 'No tweaks declared.';
      })
      .catch((error) => {
        document.getElementById('status').textContent = `Failed to load state: ${error}`;
      });
  </script>
</body>
</html>
"""


def create_playground_server(
    spec_path: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> PlaygroundHTTPServer:
    """Create a cache-free playground HTTP server for ``spec_path``.

    The initial state is loaded before binding the server so CLI startup
    fails before serving when the spec cannot render.
    """

    resolved_spec = spec_path.expanduser().resolve()
    startup_state = load_playground_state(resolved_spec)
    server = PlaygroundHTTPServer((host, port), _PlaygroundRequestHandler)
    server.spec_path = resolved_spec
    server.startup_state = startup_state
    return server


def playground_url(server: ThreadingHTTPServer) -> str:
    """Return the local URL for a bound playground server."""

    host, port = server.server_address[:2]
    return f"http://{host}:{port}/"


def serialize_playground_state(state: PlaygroundState) -> dict[str, Any]:
    """Convert playground state dataclasses to the HTTP JSON shape."""

    return {
        "specPath": str(state.spec_path),
        "valuesPath": str(state.values_path),
        "pages": [
            {
                "pageNumber": page.page_number,
                "pageId": page.page_id,
                "filename": page.filename,
                "svg": page.svg,
            }
            for page in state.pages
        ],
        "tweaks": [
            {
                "key": tweak.key,
                "group": tweak.group,
                "name": tweak.name,
                "kind": tweak.kind,
                "mode": tweak.mode,
                "value": tweak.value,
                "default": tweak.default,
                "cssVar": tweak.css_var,
                "label": tweak.label,
                "min": tweak.min,
                "max": tweak.max,
                "options": list(tweak.options) if tweak.options is not None else None,
            }
            for tweak in state.tweaks
        ],
        "values": dict(state.values),
        "diagnostics": [_serialize_diagnostic(diagnostic) for diagnostic in state.diagnostics],
    }


def _serialize_diagnostic(diagnostic: Any) -> dict[str, Any]:
    if hasattr(diagnostic, "severity") and hasattr(diagnostic, "message"):
        return {
            "severity": diagnostic.severity,
            "key": diagnostic.key,
            "message": diagnostic.message,
        }
    if hasattr(diagnostic, "__dataclass_fields__"):
        return asdict(diagnostic)
    return {"severity": "error", "key": None, "message": str(diagnostic)}


class _PlaygroundRequestHandler(BaseHTTPRequestHandler):
    server: PlaygroundHTTPServer

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path
        if path == "/":
            self._send_text(HTTPStatus.OK, PLAYGROUND_HTML, content_type="text/html; charset=utf-8")
            return
        if path == "/api/state":
            try:
                state = load_playground_state(self.server.spec_path)
            except Exception as exc:  # pragma: no cover - exact exception types vary by spec failure
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"diagnostics": [_error_payload(str(exc))]},
                )
                return
            self._send_json(HTTPStatus.OK, serialize_playground_state(state))
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"diagnostics": [_error_payload("not found")]})

    def do_PATCH(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlsplit(self.path).path
        if path != "/api/tweaks":
            self._send_json(HTTPStatus.NOT_FOUND, {"diagnostics": [_error_payload("not found")]})
            return

        try:
            payload = self._read_json_body()
            updates = _updates_from_payload(payload)
            state = apply_tweak_update(self.server.spec_path, updates)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"diagnostics": [_error_payload(str(exc))]})
            return
        except PlaygroundUpdateError as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"diagnostics": [_serialize_diagnostic(diagnostic) for diagnostic in exc.diagnostics]},
            )
            return
        except Exception as exc:  # pragma: no cover - exact exception types vary by spec failure
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"diagnostics": [_error_payload(str(exc))]},
            )
            return

        self._send_json(HTTPStatus.OK, serialize_playground_state(state))

    def log_message(self, format: str, *args: object) -> None:
        """Suppress noisy per-request stderr logging in tests and CLI."""

        return

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if not body:
            raise ValueError("request body must be JSON")
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: HTTPStatus, body: str, *, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _updates_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "updates" in payload:
        updates = payload["updates"]
        if not isinstance(updates, dict):
            raise ValueError("'updates' must be a JSON object")
        return dict(updates)
    if "key" in payload and "value" in payload:
        key = payload["key"]
        if not isinstance(key, str):
            raise ValueError("'key' must be a string")
        return {key: payload["value"]}
    raise ValueError("expected {'updates': {...}} or {'key': ..., 'value': ...}")


def _error_payload(message: str) -> dict[str, Any]:
    return {"severity": "error", "key": None, "message": message}
