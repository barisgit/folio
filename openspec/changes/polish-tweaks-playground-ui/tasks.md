## 1. Frontend asset scaffold

- [x] 1.1 Choose and document the minimal TypeScript/CSS build tool for the playground UI, keeping it developer-only and out of Folio runtime dependencies.
- [x] 1.2 Add authored playground frontend source under a clear repo location such as `src/folio/playground_ui/`.
- [x] 1.3 Add a deterministic build command that emits compiled assets into a package-included location such as `src/folio/services/playground_assets/`.
- [x] 1.4 Add or update package/build checks so missing or stale compiled playground assets fail with an actionable rebuild command.
- [x] 1.5 Verify built wheel/sdist package data can expose the compiled assets through `importlib.resources`.

## 2. Server static asset integration

- [x] 2.1 Replace normal `GET /` handling in `src/folio/services/playground_server.py` so it serves packaged `index.html` instead of the embedded monolithic `PLAYGROUND_HTML` string.
- [x] 2.2 Add safe static asset serving for compiled JavaScript/CSS/assets, including content types, no-cache headers appropriate for local dev, and path traversal rejection.
- [x] 2.3 Preserve `GET /api/state` and `PATCH /api/tweaks` behavior and response shapes for the compiled frontend.
- [x] 2.4 Remove or reduce `PLAYGROUND_HTML` after asset serving is covered by tests.
- [x] 2.5 Add server tests for `GET /`, static asset success, missing asset handling, traversal rejection, and unchanged JSON endpoint behavior.

## 3. TypeScript state and API client

- [x] 3.1 Define TypeScript types matching serialized playground state, pages, tweak metadata, values, diagnostics, and update responses.
- [x] 3.2 Implement `GET /api/state` loading with loading, success, and render-error states.
- [x] 3.3 Implement debounced `PATCH /api/tweaks` persistence with per-control pending, accepted, and rejected status.
- [x] 3.4 Preserve local draft values while server updates are in flight or rerender responses arrive.
- [x] 3.5 Preserve immediate live CSS-variable updates using the existing `cssVar` metadata and unit-aware value formatting.
- [x] 3.6 Preserve rerender fallback behavior for rebuild-mode or derived/non-live contexts by replacing page previews from server state.

## 4. Document workspace UI

- [x] 4.1 Render all returned pages as separate page cards in a continuous scrollable canvas.
- [x] 4.2 Add visible page labels and selected-page highlighting.
- [x] 4.3 Add page navigation controls that select a page and scroll its card into view without losing draft tweak edits.
- [x] 4.4 Add zoom controls for `fit width`, `fit page`, and `100%`, preserving SVG aspect ratios.
- [x] 4.5 Add empty and render-failure workspace states that do not show stale page SVG output.
- [x] 4.6 Verify multi-page starter/demo documents are usable in the workspace manually or with targeted DOM/browser tests if available.

## 5. Polished tweak inspector

- [x] 5.1 Group controls by tweak group or dotted-key prefix while preserving labels, kinds, bounds, options, edit modes, and resolved values.
- [x] 5.2 Keep color, numeric, choice, preset, and font-choice controls functionally equivalent to the current playground.
- [x] 5.3 Show per-control validation diagnostics for rejected edits without overwriting the user's draft value.
- [x] 5.4 Show global diagnostics and render warnings without hiding otherwise valid controls.
- [x] 5.5 Show clear save/update/error status for pending PATCH requests and rerenders.
- [x] 5.6 Add a polished no-tweaks empty state while keeping page previews visible.

## 6. Responsive layout and accessibility pass

- [x] 6.1 Implement desktop layout with a scrollable workspace and usable side inspector.
- [x] 6.2 Implement narrow layout that keeps navigation, zoom, diagnostics, and tweak controls reachable without whole-page horizontal scrolling.
- [x] 6.3 Ensure controls have labels, buttons expose accessible names, and diagnostic/status areas are announced or discoverable.
- [x] 6.4 Check keyboard usability for page navigation, zoom selection, and tweak controls.

## 7. Documentation and guidance

- [x] 7.1 Update generated starter README copy to describe the improved `folio dev` workspace and explicitly avoid any Node/npm requirement for project users.
- [x] 7.2 Update the bundled Folio skill to describe the polished playground workflow, packaged runtime assets, and production verification expectations.
- [x] 7.3 Add maintainer-facing notes for rebuilding playground frontend assets and for verifying package-data inclusion.

## 8. Verification

- [x] 8.1 Run frontend build/check commands and confirm compiled assets are current.
- [x] 8.2 Run targeted server/playground tests for static assets, JSON API preservation, live updates, rerender fallback, and no-cache behavior.
- [x] 8.3 Run starter-template and skill tests affected by README/skill updates.
- [x] 8.4 Run full Python test suite.
- [x] 8.5 Run `openspec validate polish-tweaks-playground-ui --strict`.
- [x] 8.6 Manually smoke-test `uv run folio dev <starter-project> --no-open` in a browser and confirm multi-page scroll, page selection, zoom, inspector edits, diagnostics, and persisted `theme.toml` behavior.
