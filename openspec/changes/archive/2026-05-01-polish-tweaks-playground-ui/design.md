## Context

`add-tweaks-playground` delivered the first local `folio dev` playground: a stdlib HTTP server with `GET /`, `GET /api/state`, and `PATCH /api/tweaks`; playground render mode with live CSS custom properties; debounced persistence to `theme.toml`; rerender fallback; and cache isolation from `folio build`. The browser shell is still embedded as a large `PLAYGROUND_HTML` string in `src/folio/services/playground_server.py`, which makes the UI hard to evolve and produces a minimal single-preview layout rather than a real document workspace.

This change is a UI/build-pipeline refinement. It should not reopen the tweak model or server semantics. The server remains local, stdlib-based, and Python-only at runtime. TypeScript/CSS tooling is allowed only for repository development and release packaging, with compiled assets committed or generated before packaging so installed users can run `folio dev` without Bun or Node.

## Goals / Non-Goals

**Goals:**

- Move the playground frontend out of Python string literals into maintainable TypeScript and CSS source.
- Serve compiled, package-included static assets from `folio dev` with no Bun/Node runtime requirement.
- Present rendered pages as a document workspace: scrollable canvas, page cards, labels, current-page awareness, navigation, and zoom controls.
- Improve the tweak inspector with grouped controls, status/diagnostic states, responsive layout, and clear persistence feedback.
- Preserve current server behavior: existing JSON endpoints, live CSS-var edits, debounced `PATCH /api/tweaks`, rerender fallback, no build-cache writes, and concrete production builds.

**Non-Goals:**

- Multiple named themes or theme selection.
- Collaboration, remote sharing, authentication, WebSockets, or server-sent events.
- Arbitrary Python editing from the browser.
- Replacing the stdlib HTTP server with ASGI/FastAPI/aiohttp.
- Changing `folio build`, export, reconcile, or tweak validation semantics.

## Decisions

### 1. Split source assets from packaged assets

Use a source directory for authored frontend code and a package-data directory for compiled assets:

- `src/folio/playground_ui/` — TypeScript/CSS source, build config, and small local README for maintainers.
- `src/folio/services/playground_assets/` — compiled `index.html`, JS, CSS, and any small static assets served by `folio dev`.

`playground_server.py` should load assets with `importlib.resources.files("folio.services.playground_assets")` rather than reading relative filesystem paths. This keeps installed wheels and editable installs on the same path.

Alternatives considered:

- Keep improving `PLAYGROUND_HTML`: simple but continues to make UI work brittle and untestable.
- Serve source files directly: avoids a build step but removes TypeScript bundling and package determinism.
- Put compiled assets outside `src/folio`: easier for frontend tooling, but harder to guarantee wheel/sdist inclusion.

### 2. Keep Bun as release-only tooling

The frontend build may use a small TypeScript bundler such as esbuild or Vite, but it must be invoked only by maintainers and release packaging. Installed users running `folio dev` must only need Python package assets. The repo should expose explicit developer commands, for example:

- `bun run build:playground` for compiling the UI.
- a Python/package build hook that runs `bun install --frozen-lockfile` and `bun run build:playground` before verifying the compiled assets.

Because this repository currently uses Hatch and already has a custom build hook for generated docs, the implementation extends that hook so `uv build` and `python -m build` rebuild the playground assets before stale checks. Bun is a packaging prerequisite, not a Folio runtime dependency.

Alternatives considered:

- Add Bun or Node as an optional runtime dependency: rejected; it violates the lightweight installed-user requirement.
- Only check committed assets during Hatch build: rejected after review because release/package builds should regenerate assets first.
- Avoid TypeScript: possible, but the user explicitly asked whether to use TypeScript and the UI will benefit from typed state and modular code.

### 3. Preserve the current JSON API

Keep these behavioral endpoints:

- `GET /` returns the packaged `index.html` shell.
- `GET /api/state` returns the current serialized `PlaygroundState`.
- `PATCH /api/tweaks` validates/persists updates and returns the existing acknowledgement/state payload.

Add only narrow static asset endpoints, such as `GET /assets/<path>` or hashed file references from `index.html`, for compiled JS/CSS. Static serving must prevent path traversal and should set content types and no-cache headers suitable for local development.

Alternatives considered:

- Change API shape while redesigning the UI: rejected; the current API is already tested and sufficient.
- Use WebSockets for updates: rejected for scope; debounced PATCH plus explicit state refresh remains adequate.

### 4. UI state model

The TypeScript app should keep a small client-side state model:

- `serverState`: last accepted `GET /api/state` or rebuild response.
- `draftValues`: current local control values keyed by dotted tweak key.
- `pendingUpdates`: per-key debounce/flight status for persistence feedback.
- `selectedPageId` or index: current page used for navigation/highlighting.
- `zoomMode`: `fit-width`, `fit-page`, or `actual-size`.
- `diagnostics`: global and control-scoped diagnostics.

Live-mode controls continue to update CSS custom properties immediately on the preview root. Accepted updates preserve current drafts; rejected updates show control diagnostics without writing `theme.toml`. Rebuild/derived changes refresh the page list from server state when the debounce completes.

### 5. Document workspace layout

The compiled UI should render all returned pages as page cards in a continuous scroll canvas. Each card shows a label such as `Page 1`, contains the server-rendered SVG, and can be selected by click or navigation controls. The current page should update when a user scrolls or clicks a card, and navigation controls should scroll the selected card into view.

Zoom modes are client-side transforms/layout choices over the SVG preview:

- `fit width`: scale each page card to the workspace width.
- `fit page`: scale selected/full pages so one page fits the viewport when practical.
- `100%`: use the SVG's natural rendered dimensions.

The right inspector remains sticky/scrollable on desktop and moves below or into a responsive drawer-like layout on narrow screens.

### 6. Migration from embedded HTML

`PLAYGROUND_HTML` should be removed or reduced to a tiny fallback used only for catastrophic packaged-asset lookup failures. Normal operation must serve the compiled asset files. Existing server serialization functions and playground service functions should remain Python-owned and tested independently of the UI bundle.

## Risks / Trade-offs

- [Risk] Committed compiled assets drift from TypeScript source. → Add a deterministic frontend build command and a package/build or test check that fails with a clear regeneration command.
- [Risk] Package data is missing from wheels/sdists. → Add packaging tests that build or inspect installed resources and assert `index.html`, JS, and CSS are available through `importlib.resources`.
- [Risk] Static asset serving introduces path traversal. → Normalize requested asset paths and reject `..`, absolute paths, directories, and missing files with safe HTTP statuses.
- [Risk] UI becomes too framework-heavy for a small local tool. → Start with TypeScript modules and plain DOM/CSS; introduce a framework only if implementation complexity proves higher without one.
- [Risk] Scroll/current-page detection is flaky in tests. → Keep DOM logic small and test pure state helpers where possible; use targeted browser/manual verification for visual behavior if no browser test harness is present.
- [Risk] Live CSS updates and rerender fallback regress during UI rewrite. → Reuse the existing API contract and add regression tests around serialized CSS variables, PATCH behavior, and no-cache rendering.

## Migration Plan

1. Add frontend source and compiled asset directories without changing server behavior.
2. Teach the server to serve packaged `index.html` and static assets while preserving existing JSON endpoints.
3. Port the current UI behavior to TypeScript/CSS with equivalent tests.
4. Add the polished workspace, navigation, zoom, diagnostics, and responsive inspector.
5. Add packaging/build checks and update README/skill/starter docs.
6. Remove the embedded monolithic HTML once asset serving is covered by tests.

Rollback is straightforward: restore the previous embedded HTML serving path and keep the existing Python service/API code unchanged.

## Open Questions

- Exact frontend build tool: esbuild is the smallest likely default; Vite is acceptable if it materially simplifies asset output and dev ergonomics.
- Whether compiled assets are always committed or generated during release preparation. The spec requires packaged assets to exist at runtime; implementation should choose the lowest-friction workflow and test it.
- Whether current-page tracking uses IntersectionObserver in browser code or simpler click/navigation-only selection for v1. The requirement allows current page highlighting; implementation can start simple if robust.
