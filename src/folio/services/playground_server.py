"""Stdlib HTTP server for the Folio tweak playground."""

from __future__ import annotations

import json
import threading
import time
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
    update_debouncer: _PlaygroundUpdateDebouncer


PLAYGROUND_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Folio Tweaks Playground</title>
  <style>
    :root { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #10131a; color: #f4f6fb; }
    button, input, select { font: inherit; }
    #folio-playground { min-height: 100vh; display: grid; grid-template-columns: minmax(0, 1fr) 360px; }
    .preview-pane { padding: 24px; overflow: auto; }
    .toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
    .toolbar h1 { font-size: 18px; margin: 0 auto 0 0; }
    #page-selector { min-width: 180px; }
    #preview-container { background: #f7f7f7; border-radius: 16px; padding: 24px; min-height: 480px; box-shadow: 0 24px 70px rgba(0, 0, 0, 0.35); }
    #preview-frame svg { display: block; max-width: 100%; height: auto; margin: 0 auto; }
    .panel { border-left: 1px solid rgba(255, 255, 255, 0.12); background: #171b25; padding: 24px; overflow: auto; }
    .panel h2 { font-size: 16px; margin: 0 0 12px; }
    #status { color: #a9b2c7; margin: 0 0 16px; }
    #diagnostics { margin: 0 0 16px; padding: 0; list-style: none; }
    #diagnostics li { background: #4b1d25; border: 1px solid #a7475a; border-radius: 10px; color: #ffdce4; margin-bottom: 8px; padding: 8px 10px; }
    .tweak-control { border-top: 1px solid rgba(255, 255, 255, 0.1); padding: 14px 0; }
    .tweak-control label { display: block; font-weight: 700; margin-bottom: 6px; }
    .tweak-meta { color: #95a0b8; font-size: 12px; margin-bottom: 8px; }
    .tweak-row { display: flex; gap: 8px; align-items: center; }
    .tweak-row input[type="text"], .tweak-row input[type="number"], .tweak-row select { flex: 1; min-width: 0; }
    .tweak-row input[type="range"] { flex: 1; }
    .control-diagnostic { color: #ffb4c2; font-size: 12px; margin-top: 6px; min-height: 1em; }
    .is-invalid input, .is-invalid select { outline: 2px solid #ff6b84; }
    .empty { color: #95a0b8; font-style: italic; }
    @media (max-width: 900px) { #folio-playground { grid-template-columns: 1fr; } .panel { border-left: 0; border-top: 1px solid rgba(255, 255, 255, 0.12); } }
  </style>
</head>
<body>
  <main id="folio-playground">
    <section class="preview-pane" aria-label="Rendered page preview">
      <div class="toolbar">
        <h1>Folio Tweaks Playground</h1>
        <label for="page-selector">Page</label>
        <select id="page-selector" aria-label="Select page"></select>
      </div>
      <div id="preview-container">
        <div id="preview-frame" aria-live="polite"></div>
      </div>
    </section>
    <aside class="panel" aria-label="Tweak controls">
      <h2>Tweaks</h2>
      <p id="status">Loading tweak state…</p>
      <ul id="diagnostics" aria-live="polite"></ul>
      <section id="tweak-panel" aria-label="Tweaks"></section>
    </aside>
  </main>
  <script>
    const API_STATE = '/api/state';
    const API_TWEAKS = '/api/tweaks';
    const DEBOUNCE_MS = 250;
    const NUMERIC_KINDS = new Set(['size_pt', 'size_mm', 'opacity', 'letter_spacing', 'stroke_width']);

    let playgroundState = null;
    let selectedPageIndex = 0;
    let draftValues = {};
    const pendingTimers = new Map();

    const statusEl = document.getElementById('status');
    const diagnosticsEl = document.getElementById('diagnostics');
    const tweakPanelEl = document.getElementById('tweak-panel');
    const pageSelectorEl = document.getElementById('page-selector');
    const previewContainerEl = document.getElementById('preview-container');
    const previewFrameEl = document.getElementById('preview-frame');

    function setStatus(message) {
      statusEl.textContent = message;
    }

    function displayDiagnostics(diagnostics) {
      diagnosticsEl.innerHTML = '';
      document.querySelectorAll('.tweak-control').forEach((node) => node.classList.remove('is-invalid'));
      document.querySelectorAll('.control-diagnostic').forEach((node) => { node.textContent = ''; });
      for (const diagnostic of diagnostics || []) {
        const item = document.createElement('li');
        item.textContent = diagnostic.key ? `${diagnostic.key}: ${diagnostic.message}` : diagnostic.message;
        diagnosticsEl.appendChild(item);
        if (diagnostic.key) {
          const control = document.querySelector(`[data-tweak-key="${CSS.escape(diagnostic.key)}"]`);
          if (control) {
            control.classList.add('is-invalid');
            const detail = control.querySelector('.control-diagnostic');
            if (detail) detail.textContent = diagnostic.message;
          }
        }
      }
    }

    function mergeState(nextState) {
      playgroundState = nextState;
      for (const tweak of nextState.tweaks) {
        if (!(tweak.key in draftValues)) {
          draftValues[tweak.key] = nextState.values[tweak.key] ?? tweak.value ?? tweak.default;
        }
      }
    }

    function renderPageSelector() {
      pageSelectorEl.innerHTML = '';
      const pages = playgroundState?.pages || [];
      pageSelectorEl.hidden = pages.length <= 1;
      pageSelectorEl.previousElementSibling.hidden = pages.length <= 1;
      pages.forEach((page, index) => {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = `Page ${page.pageNumber}: ${page.filename}`;
        pageSelectorEl.appendChild(option);
      });
      if (selectedPageIndex >= pages.length) selectedPageIndex = 0;
      pageSelectorEl.value = String(selectedPageIndex);
    }

    function applyLiveCssVars() {
      if (!playgroundState) return;
      for (const tweak of playgroundState.tweaks) {
        if (tweak.mode === 'live' && tweak.cssVar) {
          const value = draftValues[tweak.key] ?? playgroundState.values[tweak.key] ?? tweak.default;
          previewContainerEl.style.setProperty(tweak.cssVar, String(value));
        }
      }
    }

    function renderPreview() {
      const pages = playgroundState?.pages || [];
      if (!pages.length) {
        previewFrameEl.innerHTML = '<p class="empty">No pages rendered.</p>';
        return;
      }
      previewFrameEl.innerHTML = pages[selectedPageIndex].svg;
      applyLiveCssVars();
    }

    function controlInputType(tweak) {
      if (tweak.kind === 'color') return 'color';
      if (NUMERIC_KINDS.has(tweak.kind)) return 'number';
      return 'text';
    }

    function normalizeInputValue(tweak, value) {
      if (NUMERIC_KINDS.has(tweak.kind) && value !== '') return Number(value);
      return value;
    }

    function buildInput(tweak) {
      if ((tweak.kind === 'choice' || tweak.kind === 'preset' || tweak.kind === 'font_choice') && Array.isArray(tweak.options)) {
        const select = document.createElement('select');
        for (const optionValue of tweak.options) {
          const option = document.createElement('option');
          option.value = optionValue;
          option.textContent = optionValue;
          select.appendChild(option);
        }
        return select;
      }

      const input = document.createElement('input');
      input.type = controlInputType(tweak);
      if (input.type === 'number') {
        input.step = tweak.kind === 'opacity' ? '0.01' : '0.1';
        if (tweak.min !== null && tweak.min !== undefined) input.min = String(tweak.min);
        if (tweak.max !== null && tweak.max !== undefined) input.max = String(tweak.max);
      }
      return input;
    }

    function renderControls() {
      tweakPanelEl.innerHTML = '';
      const tweaks = playgroundState?.tweaks || [];
      if (!tweaks.length) {
        tweakPanelEl.innerHTML = '<p class="empty">No tweaks declared in this spec.</p>';
        return;
      }

      for (const tweak of tweaks) {
        const wrapper = document.createElement('article');
        wrapper.className = 'tweak-control';
        wrapper.dataset.tweakKey = tweak.key;

        const label = document.createElement('label');
        label.textContent = tweak.label || tweak.name || tweak.key;
        label.htmlFor = `tweak-${tweak.key.replace(/[^a-z0-9_-]/gi, '-')}`;

        const meta = document.createElement('div');
        meta.className = 'tweak-meta';
        meta.textContent = `${tweak.key} · ${tweak.kind} · ${tweak.mode}`;

        const row = document.createElement('div');
        row.className = 'tweak-row';
        const input = buildInput(tweak);
        input.id = label.htmlFor;
        input.value = String(draftValues[tweak.key] ?? playgroundState.values[tweak.key] ?? tweak.value ?? tweak.default ?? '');
        input.addEventListener('input', () => handleTweakInput(tweak, input.value));
        input.addEventListener('change', () => handleTweakInput(tweak, input.value));
        row.appendChild(input);

        if (input.type === 'number' && tweak.min !== null && tweak.min !== undefined && tweak.max !== null && tweak.max !== undefined) {
          const range = document.createElement('input');
          range.type = 'range';
          range.min = String(tweak.min);
          range.max = String(tweak.max);
          range.step = input.step;
          range.value = input.value;
          range.addEventListener('input', () => {
            input.value = range.value;
            handleTweakInput(tweak, range.value);
          });
          input.addEventListener('input', () => { range.value = input.value; });
          row.appendChild(range);
        }

        const diagnostic = document.createElement('div');
        diagnostic.className = 'control-diagnostic';

        wrapper.append(label, meta, row, diagnostic);
        tweakPanelEl.appendChild(wrapper);
      }
    }

    function renderAll() {
      renderPageSelector();
      renderPreview();
      renderControls();
      displayDiagnostics(playgroundState?.diagnostics || []);
      setStatus(playgroundState?.tweaks?.length ? `${playgroundState.tweaks.length} tweak(s) loaded.` : 'No tweaks declared.');
    }

    function schedulePatch(tweak) {
      if (pendingTimers.has(tweak.key)) clearTimeout(pendingTimers.get(tweak.key));
      pendingTimers.set(tweak.key, setTimeout(() => patchTweak(tweak), DEBOUNCE_MS));
    }

    async function patchTweak(tweak) {
      pendingTimers.delete(tweak.key);
      if (tweak.mode !== 'live') setStatus('Rendering updated preview…');
      else setStatus('Saving tweak…');
      try {
        const response = await fetch(API_TWEAKS, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: tweak.key, value: draftValues[tweak.key] }),
        });
        const payload = await response.json();
        if (!response.ok) {
          displayDiagnostics(payload.diagnostics || [{ severity: 'error', key: tweak.key, message: 'Update rejected.' }]);
          setStatus('Update rejected.');
          return;
        }
        mergeState(payload);
        renderAll();
      } catch (error) {
        displayDiagnostics([{ severity: 'error', key: tweak.key, message: String(error) }]);
        setStatus('Update failed.');
      }
    }

    function handleTweakInput(tweak, rawValue) {
      const value = normalizeInputValue(tweak, rawValue);
      draftValues[tweak.key] = value;
      if (tweak.mode === 'live' && tweak.cssVar) {
        previewContainerEl.style.setProperty(tweak.cssVar, String(value));
        setStatus('Preview updated. Saving…');
      } else {
        setStatus('Waiting to rerender…');
      }
      schedulePatch(tweak);
    }

    pageSelectorEl.addEventListener('change', () => {
      selectedPageIndex = Number(pageSelectorEl.value || 0);
      renderPreview();
    });

    fetch(API_STATE)
      .then((response) => response.json())
      .then((state) => {
        mergeState(state);
        renderAll();
      })
      .catch((error) => {
        displayDiagnostics([{ severity: 'error', key: null, message: `Failed to load state: ${error}` }]);
        setStatus('Failed to load state.');
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
            state = self.server.update_debouncer.apply(updates)
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
