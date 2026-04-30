## Why

The current `folio dev` playground proves the tweak model works, but the UI is still a minimal embedded HTML shell: it shows one oversized preview area, weak page navigation, and basic controls that do not feel like a document design workspace. Now that the model/server behavior is complete and archived, the next step is to make the playground usable for real multi-page documents while keeping Folio lightweight for installed users.

## What Changes

- Replace the monolithic embedded `PLAYGROUND_HTML` string with packaged static frontend assets compiled from TypeScript and CSS source.
- Keep Node/TypeScript as a repository/developer build-time dependency only; installed Folio users running `folio dev` must not need Node, npm, or a frontend toolchain.
- Serve the compiled playground UI from the existing stdlib HTTP server, preserving the current JSON API contract unless narrow static asset endpoints are needed.
- Redesign the UI as a document/page workspace with a scrollable canvas, page cards, page labels, current-page navigation, and zoom modes (`fit width`, `fit page`, `100%`).
- Polish the right-side tweak inspector with clearer control grouping, validation/diagnostic display, loading and error states, and responsive behavior.
- Preserve existing playground behavior: live CSS-variable updates, debounced `PATCH /api/tweaks` persistence, rerender fallback for rebuild/derived usages, no build-cache writes, and concrete authoritative `folio build` output.
- Out of scope: multiple named themes, collaboration, WebSockets, arbitrary Python source editing, or changing production build/export semantics.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tweaks-playground`: require the playground UI to be served from packaged compiled assets, present a polished document/page workspace, and keep the current local API and editing guarantees.
- `starter-template`: update starter documentation expectations so generated projects describe the improved document workspace without implying Node is required for `folio dev`.
- `folio-skill`: update bundled agent guidance to describe the polished playground workflow and warn that frontend asset source/build tooling is Folio-maintainer-only, not a project/user runtime requirement.

## Impact

- Affected code likely includes `src/folio/services/playground_server.py`, a new frontend source directory, package-data configuration, tests for packaged assets/server responses, and documentation/skill/starter text.
- The `folio dev` HTTP API remains local and stdlib-based: `GET /`, `GET /api/state`, and `PATCH /api/tweaks` continue to be the behavioral contract.
- Python package artifacts must include compiled playground assets in wheels and sdists.
- Development workflows gain a frontend build/check command, but runtime users do not gain a Node dependency.
