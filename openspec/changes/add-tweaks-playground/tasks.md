## 1. Renderer Playground Mode CSS Variables

- [x] 1.1 Activate the renderer's `playground` mode (introduced in `add-tweaks-model`) to emit `var(--folio-tweak-<dotted-key-with-dashes>, <fallback>)` for live-safe attributes only: `fill`, `stroke`, `opacity`, `fill-opacity`, `stroke-opacity`, `font-size`, `letter-spacing`, and presentation `stroke-width`.
- [x] 1.2 Ensure attributes outside the live-safe set, attributes backed by rebuild-mode tweaks, and all geometry attributes remain concrete in playground mode.
- [x] 1.3 Add a regression test that scans `folio build` SVG output and asserts no `var(--folio-tweak-` substring appears for any spec, including specs that declare live-mode tweaks.
- [x] 1.4 Add renderer tests for playground-mode output: live-safe attributes contain `var(--folio-tweak-...)` with concrete fallbacks, and non-live-safe attributes stay concrete.

## 2. Spec Load Helper Cache Isolation

- [x] 2.1 Add an option to the spec load/render service helper that suppresses last-build cache writes; default remains "write cache" for `folio build`.
- [x] 2.2 Wire the dev server to use the no-cache option for every render and rerender.
- [x] 2.3 Add tests that running `folio dev` (or its underlying server entry point) does not modify the last-build cache directory.

## 3. `folio dev` Command and HTTP Server

- [ ] 3.1 Add a `folio dev` Typer command with spec resolution shared with `folio build`, plus `--host` (default `127.0.0.1`), `--port`, and `--open/--no-open` options.
- [ ] 3.2 Implement a loopback HTTP server using stdlib server primitives that serves the playground shell, static assets, and JSON endpoints; report the served URL on stdout.
- [ ] 3.3 Implement `GET /` returning the playground shell HTML.
- [ ] 3.4 Implement `GET /api/state` returning rendered pages, tweak schema, resolved values, modes, warnings, and render diagnostics.
- [ ] 3.5 Implement `PATCH /api/tweaks` that validates a value update against the tweak declaration, writes `<spec_dir>/theme.toml` deterministically on accept, and rejects invalid edits without writing.
- [ ] 3.6 Implement `--open` browser-launch behavior with a safe no-op fallback in headless or unsupported environments.
- [ ] 3.7 Implement startup behavior for missing/invalid spec, no-tweaks empty state, and configurable host/port.

## 4. Playground UI

- [ ] 4.1 Build the minimal HTML/JS playground shell served by `folio dev` with page preview, page selection when multiple pages exist, and a tweak panel.
- [ ] 4.2 Render controls per declaration type: color picker, numeric/range inputs with declared `min`/`max`, opacity, letter spacing, choices/presets/font choices.
- [ ] 4.3 Apply live-mode edits immediately by setting the corresponding `--folio-tweak-...` custom property on the preview container.
- [ ] 4.4 For rebuild-mode edits, show progress and replace rendered SVG previews after the rebuild completes.
- [ ] 4.5 Show validation and render diagnostics next to affected controls or in a visible error area.
- [ ] 4.6 Preserve pending edit state across page-selector changes.

## 5. Edit Persistence and Debounce

- [ ] 5.1 Debounce rebuild-mode edits server-side so dragging a slider does not trigger one rebuild per keystroke.
- [ ] 5.2 Debounce live-mode persistence so disk writes are not issued for every intermediate value while the browser CSS variable updates immediately.
- [x] 5.3 Implement last-write-wins behavior for `theme.toml`: reread on each render; on accepted PATCH, overwrite the file with the playground's view of values.
- [ ] 5.4 Add server/API tests for startup success, startup render failure, no-tweaks empty state, live edit persistence, rebuild edit rerender, rejected invalid edits, debounce coalescing, last-write-wins after external edit, and cache isolation.

## 6. Skill and Starter README

- [ ] 6.1 Update the bundled Folio `SKILL.md` to introduce `folio dev` as the browser playground for `folio.dsl.tweaks`-declared values, persisting to `<spec_dir>/theme.toml`, and to keep the production pipeline authoritative.
- [ ] 6.2 Update the starter `README.md` to add a `folio dev` example while preserving the production pipeline guidance from `add-tweaks-model`.

## 7. Verification

- [ ] 7.1 Run targeted unit tests for the renderer playground mode, dev server endpoints, edit persistence, and debounce behavior.
- [ ] 7.2 Run the build-output regression test confirming `folio build` SVGs contain no `var(--folio-tweak-` references.
- [ ] 7.3 Run the full project test suite.
- [ ] 7.4 Run `openspec validate add-tweaks-playground --strict` and fix any proposal/spec/task validation issues.
