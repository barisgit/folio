## Why

`add-tweaks-model` adds the tweak declaration model, persisted `theme.toml` values, validation, and renderer mode flag, but production-only. Designers and non-coders still cannot tune approved values visually; the edit loop remains "edit TOML, rerun build, inspect output". This change adds a local browser playground (`folio dev`) that surfaces declared tweaks, persists edits to `theme.toml`, and shows immediate visual feedback for live-eligible values while keeping `folio build` authoritative for exports.

This change depends on `add-tweaks-model`. It does not redefine the declaration model, the values file location, the validation rules, or the per-class default mode table.

## What Changes

- Add a `folio dev` Typer command with `--host` (default `127.0.0.1`), `--port`, and `--open/--no-open` options.
- Implement a loopback HTTP server that serves a self-contained HTML/JS playground plus JSON endpoints (`GET /` shell, `GET /api/state`, `PATCH /api/tweaks`).
- Implement playground rendering: extend the renderer's reserved `playground` mode to emit `var(--folio-tweak-<key>, <fallback>)` for live-safe attributes only, inside the HTML playground wrapper.
- Implement the playground UI: page preview, page selection, tweak controls per declaration type, immediate CSS-variable updates for live edits, and debounced rebuilds for rebuild-mode edits.
- Implement value-update handling: validate edits against the existing tweak validation rules, write `theme.toml` deterministically on accepted edits, reject invalid edits without writing, last-write-wins on external editor races.
- Keep playground rendering isolated from the production last-build cache: `folio dev` re-renders pages but never updates the build cache or reconcile state.
- Update the bundled Folio skill and starter README to describe `folio dev` as an optional design-tuning step alongside `folio check -> build -> rasterize -> reconcile`.
- No breaking changes: `folio build` and `folio validate` keep emitting concrete values; specs without tweaks still see an empty playground state when `folio dev` runs.

## Capabilities

### New Capabilities

- `tweaks-playground`: Defines the `folio dev` command, the loopback HTTP server endpoints, the playground rendering mode that emits CSS variables for live-safe attributes, the playground UI behavior, edit persistence rules, and cache isolation.

### Modified Capabilities

- `starter-template`: Update the generated `README.md` to mention `folio dev` as an optional design-tuning step.
- `folio-skill`: Teach agents when to use `folio dev` and that it is not a substitute for `folio check`/`folio build`/`folio rasterize`/`folio reconcile`.

The behavior change in the renderer's `playground` mode (CSS-variable emission for live-safe attributes) is owned by the new `tweaks-playground` capability and does not require a delta on `tweaks`; that capability still ships through `add-tweaks-model`.

## Impact

- Affected CLI: new `folio dev` command and development server/playground assets.
- Affected rendering: the renderer's `playground` mode (introduced in `add-tweaks-model`) starts emitting CSS custom properties for live-safe attributes; build mode is unchanged.
- Affected services: a small loopback HTTP server, value-update endpoint, and debounced rebuild loop reusing the spec load/render service helper from `add-tweaks-model`.
- Affected templates/docs/skill: starter `README.md` and bundled Folio skill text only.
- Non-goals: editing arbitrary Python from the browser, multi-user collaboration, hosted rendering, full live layout/flow recalculation, preset libraries, multi-file values, and treating playground SVGs as canonical build or reconcile inputs.

## Prerequisites

- `add-tweaks-model` must be archived before this change is implemented; this proposal assumes the tweak model, registry, `TweakValue` wrappers, `theme.toml` at `<spec_dir>/theme.toml`, validation rules, per-class default mode table, and renderer mode flag already exist.
