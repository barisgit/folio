## Context

This change builds on `add-tweaks-model`, which delivers:

- The `folio.dsl.tweaks` declaration surface, `TweakRegistry`, and `TweakValue` wrappers.
- Persisted values at `<spec_dir>/theme.toml` with `tomllib` reads and a deterministic writer.
- A spec load/render service helper that returns `BuildResult` plus a tweak registry snapshot.
- `folio validate` and `folio build` integration with concrete rendered output.
- A renderer mode flag (`build` or `playground`); in `add-tweaks-model` both modes emit concrete values.

This change adds the `folio dev` command, the playground HTTP server, the playground UI, and activates the renderer's playground mode to emit CSS custom properties for live-safe attributes.

Important constraints:

- Build/export artifacts and reconcile state must remain unaffected: `folio dev` never updates the production last-build cache.
- Loopback-only by default. The dev server is a developer tool, not a hosted service.
- Stdlib server primitives are the first choice; an ASGI stack is not required unless stdlib routing proves too awkward during implementation.
- Live CSS-variable injection must use the dedicated formatter path introduced in `add-tweaks-model`; geometry and layout attributes stay concrete and rebuild-only.

## Goals / Non-Goals

**Goals:**

- Ship `folio dev` as a local design-tuning playground for declared tweaks.
- Serve a self-contained HTML/JS UI plus JSON endpoints from a loopback HTTP server.
- Activate the renderer's playground mode to emit `var(--folio-tweak-<key>, <fallback>)` for live-safe attributes only.
- Persist accepted edits to `theme.toml` using the writer from `add-tweaks-model`.
- Provide debounced rebuild for rebuild-mode edits and immediate CSS-variable updates for live edits.
- Keep `folio dev` strictly isolated from the production build cache and reconcile state.

**Non-Goals:**

- Editing Python source from the browser.
- Multi-user collaboration, hosted rendering, or non-loopback defaults.
- Preset libraries, multi-file values, or cross-project value sharing (still owned by future changes).
- Live layout, text-flow, image, or geometry updates without rebuild.
- Replacing `folio check`, `folio build`, `folio rasterize`, or `folio reconcile` for production verification.
- A `--tweak key=value` CLI override or other ad-hoc tweak entry points.

## Decisions

1. **`folio dev` is a Typer command with a tiny stdlib HTTP server.**

   Add `folio dev [spec]` with `--host` (default `127.0.0.1`), `--port`, and `--open/--no-open`. Use Python stdlib server primitives for the first implementation; revisit only if routing/concurrency becomes painful. Print the served URL on stdout.

   Rejected: pulling in an ASGI dependency (uvicorn/starlette) for what is effectively three endpoints and static asset serving.

2. **Three endpoints are enough.**

   - `GET /` returns the playground shell HTML.
   - `GET /api/state` returns rendered pages, schema, resolved values, modes, warnings, and render diagnostics.
   - `PATCH /api/tweaks` validates a value update, writes `theme.toml` on accept, returns either a live acknowledgement or a rebuilt state.

   Static assets (JS/CSS) are bundled into the shell or served from a single static path. Anything richer can be added later without changing this contract.

3. **Activate playground rendering mode for live-safe attributes only.**

   Build mode stays concrete-only. Playground mode emits `var(--folio-tweak-<dotted-key-with-dashes>, <fallback>)` for live-eligible attributes whose declaration is `live`. Live-safe attribute set: `fill`, `stroke`, `opacity`, `fill-opacity`, `stroke-opacity`, `font-size`, `letter-spacing`, and presentation `stroke-width` where the renderer already treats it as a presentation attribute.

   Geometry attributes (`x`, `y`, `width`, `height`, `r`, page dimensions) and any rebuild-mode value remain concrete. The fallback inside `var(...)` is the resolved value at render time, so the SVG looks correct even before any CSS variable is set.

   Rationale: the dedicated formatter path is already in place from `add-tweaks-model`; this change only flips on the CSS-variable branch in playground mode.

4. **Live edits update CSS variables and persist asynchronously.**

   Browser behavior:

   - Live-mode edit: the UI updates the CSS custom property on a stable container element immediately; the same change is sent to `PATCH /api/tweaks` for persistence.
   - Rebuild-mode edit: the UI sends the change to `PATCH /api/tweaks`, the server validates and writes `theme.toml`, debounces a spec rerun, and returns updated schema/values/SVGs or diagnostics.
   - Rejected edit (validation failure): the UI surfaces the diagnostic next to the affected control; `theme.toml` is not modified.

5. **Last-write-wins on external editor races (v1).**

   `folio dev` reads `theme.toml` from disk before each render and writes deterministically on accepted edits. If the user edits `theme.toml` in an external editor while the server has it open, the next server-side write replaces the file with the playground's view of values. This is documented explicitly. A future change can add mtime-based conflict prompts.

6. **Cache isolation: playground never updates the build cache.**

   The spec load/render helper supports a flag the dev server uses to skip cache writes. Reconcile and `folio build` continue to compare against and refresh the last-build cache only.

7. **Debounce strategy.**

   Rebuild-mode edits are coalesced with a short debounce window (e.g. ~150ms) so dragging a slider does not trigger one rebuild per keystroke. Live-mode edits update the browser CSS variable immediately; persistence to `theme.toml` is also debounced to reduce disk churn.

8. **Skill and starter docs gain `folio dev` as an optional step.**

   The bundled `SKILL.md` keeps `folio check -> build -> rasterize -> reconcile` as the authoritative production pipeline and adds `folio dev` as an optional visual tuning step before final build/rasterize verification. The starter `README.md` adds a single `folio dev` example without removing the production pipeline guidance from `add-tweaks-model`.

## Risks / Trade-offs

- **Risk: live CSS variables leak into build outputs.** → Mitigation: build mode formatter never emits `var(...)`; cover with a regression test that scans build SVGs for `var(--folio-tweak-`.
- **Risk: dev server rebuilds become slow on large documents.** → Mitigation: debounce rebuild-triggering edits; consider rendering only the visible page when document is large; keep live updates for high-frequency interactions.
- **Risk: browser writes race with external editor saves.** → Mitigation: explicit last-write-wins for v1, documented in the spec; future change can add mtime/conflict prompts.
- **Risk: stdlib HTTP server limits concurrency.** → Mitigation: dev server is single-user loopback; if it becomes painful, switch to an ASGI stack in a follow-up without changing endpoint contracts.
- **Risk: reconcile reports noisy diffs if users save playground SVGs.** → Mitigation: never write playground SVGs as build cache; document that reconcile uses `folio build` outputs only.
- **Risk: live mode contains an attribute the renderer cannot safely express as a CSS variable.** → Mitigation: explicit allow-list; anything outside the list degrades to rebuild with a diagnostic.

## Migration Plan

1. Activate the renderer's playground mode CSS-variable emission for the live-safe attribute allow-list, with build mode unchanged.
2. Add the spec load/render helper option to skip last-build cache updates (used only by the dev server).
3. Add `folio dev [spec]` Typer command with `--host`, `--port`, `--open/--no-open` options.
4. Add the loopback HTTP server with `GET /`, `GET /api/state`, `PATCH /api/tweaks`.
5. Add the HTML/JS playground shell and tweak controls.
6. Wire debounced rebuild for rebuild-mode edits, immediate CSS-variable update plus debounced persistence for live-mode edits, and rejection-without-write for invalid edits.
7. Add server/API tests, renderer playground-mode tests, build-output regression test, and end-to-end CLI tests for `folio dev`.
8. Update bundled `SKILL.md` and starter `README.md`.
9. Run `openspec validate add-tweaks-playground --strict` and the full project test suite.

Rollback: remove the `folio dev` command and HTTP server, revert the renderer playground-mode CSS-variable branch (back to concrete-only), revert skill/starter README edits. The tweak model from `add-tweaks-model` continues to work because playground mode collapses cleanly back to "concrete values".
