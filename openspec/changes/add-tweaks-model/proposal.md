## Why

Folio's edit loop is agent- and developer-centric: change Python constants, rebuild, rasterize, inspect, and repeat. Before any browser playground can exist, Folio needs a typed declaration model for design-time tweaks plus a project-local TOML values file that `folio validate` and `folio build` already understand. This change delivers that foundation; the browser playground ships separately as `add-tweaks-playground`.

## What Changes

- Add first-class design-time tweak declarations to the DSL through `folio.dsl.tweaks` (re-exported from `folio.core.dsl.tweaks`).
- Introduce a spec-scoped `TweakRegistry` that collects declarations across the spec module graph and resets on every spec load.
- Return `TweakValue` wrappers from helpers that resolve to primitives in build mode and preserve metadata when assigned directly to live-eligible style/element attributes (notably `TextStyle.font_size_pt`).
- Persist user-selected tweak values in a project-local TOML file resolved as `<spec_dir>/theme.toml`; no `values_file=` override in this change.
- Validate persisted tweak values against declarations: invalid types/ranges/options are errors; unknown persisted keys are warnings.
- Make `folio validate` and `folio build` load and validate persisted tweak values, render artifacts with concrete resolved values, and refresh the last-build cache from those concrete values.
- Make the renderer mode-aware at the attribute boundary: build mode always emits concrete values; a `playground` mode is reserved (no `folio dev` consumer in this change) so a future change can emit `var(--folio-tweak-...)` for live-safe attributes without re-touching the renderer.
- Update the starter template so tweakable brand values live in `folio.dsl.tweaks` (not `tokens`); `tokens` keeps non-tweakable named values. Generated projects include a working `theme.toml`.
- Update `folio docs` index, examples validation, and the bundled Folio skill to cover tweak helpers and `theme.toml`.
- Drop `image()` from the initial helper surface; defer to a follow-up change once asset-resolution semantics are settled.
- No breaking changes: specs without tweak declarations build and validate unchanged.

## Capabilities

### New Capabilities

- `tweaks`: Defines the tweak declaration/value model, `TweakRegistry`, `TweakValue` wrappers, the public `folio.dsl.tweaks` helper surface, the per-class default edit-mode table, TOML persistence at `<spec_dir>/theme.toml`, and validation diagnostics.

### Modified Capabilities

- `python-dsl`: Expose `folio.dsl.tweaks`, allow `TweakValue` wherever the corresponding primitive is accepted, and preserve `TweakValue` (without primitive coercion) on live-eligible `TextStyle` and element-attribute fields.
- `build-and-validate`: Load and validate persisted tweak values, fail builds on invalid values, warn on unknown persisted keys, and render authoritative artifacts with concrete resolved values.
- `starter-template`: Replace tweakable brand color and text size constants in `theme.py` with tweak declarations, ship a committed `theme.toml`, and update the starter README.
- `dsl-docs`: Index public tweak helpers and validate their documentation examples.
- `folio-skill`: Teach agents about the tweak declaration model and `theme.toml` while keeping `folio check -> build -> rasterize -> reconcile` authoritative.

## Impact

- Affected DSL/API: new `folio.core.dsl.tweaks` module re-exported as `folio.dsl.tweaks`; `TextStyle` and selected element-attribute fields accept `float | TweakValue` (or `str | TweakValue` for color) without coercing at construction.
- Affected services: spec-load helper that creates a tweak context, loads `theme.toml`, executes the spec, renders the collection, and returns `BuildResult` plus a `TweakRegistry` snapshot.
- Affected CLI: `folio validate` and `folio build` route through the new helper; no new commands.
- Affected rendering: renderer gains a build/playground mode flag; build mode is the only consumer in this change and must emit concrete values for tweak-backed attributes.
- Affected templates/docs/skill: starter `theme.py`/`theme.toml`, `folio docs` index, README, bundled skill text, and docs example fixtures.
- Non-goals: any browser playground, `folio dev` server, live CSS-variable injection, `--tweak key=value` CLI overrides, `image()` tweaks, comment-preserving TOML round-tripping, multi-file/preset values, and cross-project token sync.
