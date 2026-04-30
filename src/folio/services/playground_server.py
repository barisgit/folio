"""Stdlib HTTP server for the Folio tweak playground."""

from __future__ import annotations

import json
import mimetypes
import threading
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

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
    update_debouncer: _PlaygroundUpdateDebouncer


_ASSET_PACKAGE = "folio.services.playground_assets"
_ASSET_PREFIX = "/assets/"



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
    server.update_debouncer = _PlaygroundUpdateDebouncer(resolved_spec)
    return server


class _PlaygroundUpdateDebouncer:
    """Coalesce rapid PATCH updates into one persisted render cycle."""

    def __init__(self, spec_path: Path, *, delay_seconds: float = 0.15) -> None:
        self.spec_path = spec_path
        self.delay_seconds = delay_seconds
        self._condition = threading.Condition()
        self._pending: dict[str, Any] = {}
        self._version = 0
        self._completed_version = 0
        self._deadline = 0.0
        self._worker_running = False
        self._state: PlaygroundState | None = None
        self._error: Exception | None = None

    def apply(self, updates: dict[str, Any]) -> PlaygroundState:
        """Apply updates after a quiet debounce window and return fresh state."""

        with self._condition:
            self._pending.update(updates)
            self._version += 1
            requested_version = self._version
            self._deadline = time.monotonic() + self.delay_seconds
            if not self._worker_running:
                self._worker_running = True
                threading.Thread(target=self._run, daemon=True).start()
            while self._completed_version < requested_version:
                self._condition.wait()
            if self._error is not None:
                raise self._error
            assert self._state is not None
            return self._state

    def _run(self) -> None:
        while True:
            with self._condition:
                while True:
                    remaining = self._deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._condition.wait(timeout=remaining)
                updates = dict(self._pending)
                self._pending.clear()
                apply_version = self._version

            try:
                state = apply_tweak_update(self.spec_path, updates)
                error: Exception | None = None
            except Exception as exc:  # pragma: no cover - surfaced through handler tests
                state = None
                error = exc

            with self._condition:
                self._completed_version = apply_version
                self._state = state
                self._error = error
                self._condition.notify_all()
                if self._pending:
                    continue
                self._worker_running = False
                return


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
            self._send_packaged_asset("index.html", content_type="text/html; charset=utf-8")
            return
        if path.startswith(_ASSET_PREFIX):
            self._send_static_asset(path)
            return
        if path == "/api/state":
            try:
                state = load_playground_state(self.server.spec_path)
            except Exception as exc:  # pragma: no cover - spec failures vary
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
            state = self.server.update_debouncer.apply(updates)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"diagnostics": [_error_payload(str(exc))]})
            return
        except PlaygroundUpdateError as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "diagnostics": [
                        _serialize_diagnostic(diagnostic) for diagnostic in exc.diagnostics
                    ]
                },
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
        self._send_body(status, body, content_type="application/json")

    def _send_static_asset(self, path: str) -> None:
        asset_name = unquote(path.removeprefix(_ASSET_PREFIX))
        if not _is_safe_asset_name(asset_name):
            self._send_json(HTTPStatus.NOT_FOUND, {"diagnostics": [_error_payload("not found")]})
            return
        content_type = mimetypes.guess_type(asset_name)[0] or "application/octet-stream"
        self._send_packaged_asset(asset_name, content_type=content_type)

    def _send_packaged_asset(self, asset_name: str, *, content_type: str) -> None:
        try:
            asset = resources.files(_ASSET_PACKAGE).joinpath(*PurePosixPath(asset_name).parts)
        except ModuleNotFoundError:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"diagnostics": [_error_payload("packaged playground assets are missing")]},
            )
            return
        if not asset.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"diagnostics": [_error_payload("not found")]})
            return
        self._send_body(
            HTTPStatus.OK,
            asset.read_bytes(),
            content_type=content_type,
            headers={"Cache-Control": "no-store"},
        )

    def _send_body(
        self,
        status: HTTPStatus,
        body: bytes,
        *,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        try:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return


def _is_safe_asset_name(asset_name: str) -> bool:
    path = PurePosixPath(asset_name)
    return bool(asset_name) and not path.is_absolute() and all(
        part not in {"", ".", ".."} for part in path.parts
    )


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
