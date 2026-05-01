## 1. Pydantic-backed payload models

- [ ] 1.1 Convert `PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, and `Diagnostic` in `src/folio/services/playground.py` to Pydantic v2 `BaseModel` classes with explicit JSON-serializable field types.
- [ ] 1.2 Update `serialize_playground_state` (or remove it) so that the playground server uses `model_dump(mode="json")` to produce the response payload.
- [ ] 1.3 Add `pydantic` to project dependencies in `pyproject.toml`.
- [ ] 1.4 Run `tests/test_playground_service.py` and `tests/test_playground_server.py`; payload-shape assertions must continue to pass without modification.

## 2. Types codegen helper

- [ ] 2.1 Add a maintainer-only Python module (e.g. `src/folio/_dev/gen_playground_types.py`) that imports the playground Pydantic models and emits `src/folio/playground_ui/api.generated.ts` with `PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, `Diagnostic`, and any nested types.
- [ ] 2.2 Ensure the helper is excluded from wheel and sdist artifacts via the existing `tool.hatch.build` exclude lists, and verify by inspecting a built wheel.
- [ ] 2.3 Wire the codegen helper into `src/folio/playground_ui/build.mjs` so `bun run build:playground` regenerates `api.generated.ts` before bundling.
- [ ] 2.4 Add a test (`tests/test_playground_types_codegen.py`) that runs the helper in-process and asserts the committed `api.generated.ts` matches the freshly generated output character-for-character.
- [ ] 2.5 Switch the existing `main.ts` to import its API types from the generated module and delete the hand-written interfaces.
- [ ] 2.6 Update `manifest.json` source-hash list to include `api.generated.ts` and the codegen helper path so stale-asset checks fire when either drifts.

## 3. Vite + Solid scaffold

- [ ] 3.1 Add `vite`, `solid-js`, and `vite-plugin-solid` to `devDependencies` in `package.json` and refresh `bun.lock`.
- [ ] 3.2 Add a Vite config (e.g. `src/folio/playground_ui/vite.config.ts`) that bundles the Solid app into `src/folio/services/playground_assets/playground.js` and `playground.css`, copies `index.html`, and produces deterministic filenames matching the existing asset URLs.
- [ ] 3.3 Replace `src/folio/playground_ui/main.ts` with `main.tsx` that mounts a placeholder `<App />` and verify the served `playground.js` still wires up against `index.html` end-to-end.
- [ ] 3.4 Update `build.mjs` so the build step runs Vite (after step 2.3 codegen) and continues to populate the `manifest.json` source-hash list with the new source files (`vite.config.ts`, `main.tsx`, every component module, `App.tsx`, `state.ts`, `api.ts`).
- [ ] 3.5 Verify the bundled `playground.js` size stays under 80 KB minified; if not, investigate before continuing.

## 4. Component port

- [ ] 4.1 Implement `state.ts` exporting a `createPlaygroundStore()` that owns `state`, `draftValues`, `pendingUpdates`, `selectedPageIndex`, `zoomMode`, and `globalStatus` signals plus `loadState`, `patchTweak`, and `selectPage` actions.
- [ ] 4.2 Port the diagnostics list to a `<Diagnostics />` component.
- [ ] 4.3 Port the four tweak controls to `tweaks/ColorTweak.tsx`, `tweaks/SliderTweak.tsx`, `tweaks/SelectTweak.tsx`, and `tweaks/TextNumberTweak.tsx`, preserving units, swatch behavior, range progress, and ARIA wiring.
- [ ] 4.4 Port the inspector list and group rendering to `<TweakPanel />`.
- [ ] 4.5 Port the custom page-selector dropdown to `<PageSelector />` and the zoom segmented control to `<ZoomSegments />`.
- [ ] 4.6 Port the page canvas, IntersectionObserver, and click-to-jump suppression to `<PageCanvas />`.
- [ ] 4.7 Port the topbar (brand, spec-path chip, status dot) to `<Topbar />` and assemble everything in `<App />`.
- [ ] 4.8 Delete the legacy `main.ts` once `main.tsx` covers every behavior currently exercised by the existing playground tests.

## 5. Test surface refresh

- [ ] 5.1 Update `test_packaged_js_preserves_current_ui_behavior` to assert intent-level markers (e.g. `PlaygroundState`, `PATCH /api/tweaks` URL, asset filenames) rather than vanilla-TS function names.
- [ ] 5.2 Add a small DOM smoke test (using stdlib `urllib` plus a regex check) that confirms the served `index.html` references the new bundle entry points and that the bundle exports a Solid mount call.
- [ ] 5.3 Confirm `tests/test_playground_server.py` traversal, no-cache, and JSON contract tests still pass without modification.

## 6. Documentation and skill updates

- [ ] 6.1 Update `src/folio/playground_ui/README.md` to describe the Solid + Vite + codegen workflow, list the maintainer prerequisites (Bun, Python with Pydantic), and document the rebuild command.
- [ ] 6.2 Update the bundled Folio agent skill so it reflects the typed-component playground architecture and warns against hand-editing `api.generated.ts` or compiled assets.
- [ ] 6.3 Update any cartography or codemap references (`src/folio/services/codemap.md`, `src/folio/playground_ui/` notes) that describe the old vanilla-TS UI.

## 7. Verification

- [ ] 7.1 Run `bun run build:playground` and confirm the regenerated assets and `manifest.json` are clean.
- [ ] 7.2 Run the full Python test suite (`uv run pytest`) and ensure all playground tests pass.
- [ ] 7.3 Run `openspec validate migrate-playground-to-solid-typed --strict`.
- [ ] 7.4 Run `openspec validate --specs --strict` to confirm no main-spec drift.
- [ ] 7.5 Smoke-test `uv run folio dev <starter-project> --no-open` in a browser: verify multi-page scroll, page selection, zoom modes, every tweak control kind, diagnostics rendering, debounced PATCH persistence, and `theme.toml` updates on disk.
- [ ] 7.6 Inspect the built wheel to confirm the codegen helper is excluded and the compiled `playground.js`/`playground.css`/`index.html`/`api.generated.ts` source-of-truth paths are correct.
