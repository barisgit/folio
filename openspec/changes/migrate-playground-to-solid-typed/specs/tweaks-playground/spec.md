## ADDED Requirements

### Requirement: Generated playground type contract

Folio SHALL maintain a single, generated TypeScript type module describing every JSON payload exchanged between the playground server and browser, sourced from the Python payload models.

#### Scenario: Generated types module exists in source
- **WHEN** a maintainer inspects the playground frontend source
- **THEN** the repository contains a generated TypeScript types module (e.g. `src/folio/playground_ui/api.generated.ts`) that declares both response shapes (`PlaygroundState`, `PlaygroundTweak`, `PlaygroundPage`, `Diagnostic`) and the `PATCH /api/tweaks` request shape (e.g. `TweakUpdateRequest`)
- **AND** every other playground frontend module imports those shapes from the generated module rather than redeclaring them

#### Scenario: Build step regenerates types from Python models
- **WHEN** a maintainer runs the documented playground build command
- **THEN** the build regenerates the TypeScript types module from the current Python payload models
- **AND** writes the regenerated module to the same source path used by the rest of the frontend

#### Scenario: Drift between models and committed types is detected
- **WHEN** the test suite or asset-staleness check runs
- **THEN** the check fails if the committed generated types module differs from the output produced by regenerating it against the current Python payload models
- **AND** the failure message names the playground frontend rebuild command

### Requirement: Component-based playground frontend

Folio SHALL implement the playground frontend as a component-based application using Solid and Vite, with state owned by a single store module.

#### Scenario: Frontend uses Solid components
- **WHEN** a maintainer inspects the playground frontend source
- **THEN** the UI is composed of Solid components for the topbar, page canvas, page selector, zoom segments, tweak panel, and individual tweak controls
- **AND** the components consume signals from a single playground store module

#### Scenario: Frontend uses Vite as the bundler
- **WHEN** a maintainer runs the documented playground build command
- **THEN** Vite produces the compiled bundle written to the packaged asset directory
- **AND** the produced bundle continues to be served by the existing stdlib HTTP server without changes to the runtime URL contract

#### Scenario: Server payloads are produced by typed Python models
- **WHEN** the playground server responds to `GET /api/state` or `PATCH /api/tweaks`
- **THEN** the JSON payload is produced by Python payload models that own serialization
- **AND** the payload field names, types, and nesting match the generated TypeScript types module exactly

#### Scenario: Wire shape preserved across model migration
- **WHEN** the playground server serializes a state payload using the new typed payload models
- **THEN** the emitted JSON keys, value types, and `null` handling match the legacy hand-rolled serialization byte-for-byte for any equivalent state
- **AND** existing tests asserting field names like `pageNumber`, `pageId`, `cssVar`, `specPath`, and `valuesPath` continue to pass without modification

## MODIFIED Requirements

### Requirement: Developer-only frontend build pipeline

Folio SHALL keep the playground frontend build toolchain (Solid, Vite, Bun, and the Python types-generation helper) as a repository and release-build concern, not as a runtime requirement for users of `folio dev`.

#### Scenario: Installed runtime has no Node requirement
- **WHEN** a user installs Folio from a wheel or sdist and runs `folio dev <spec>`
- **THEN** the playground starts and serves the bundled compiled UI using only Folio's Python runtime dependencies
- **AND** does not invoke `node`, `npm`, `npx`, `bun`, `vite`, or a TypeScript compiler at runtime

#### Scenario: Maintainer rebuild command
- **WHEN** a maintainer changes playground TypeScript, JSX, CSS source, or the Python payload models
- **THEN** the repository provides a documented command that regenerates the TypeScript types module and rebuilds the compiled playground assets in one step
- **AND** the generated assets are written to the package-included asset location used by `folio dev`

#### Scenario: Stale or missing compiled assets are detected
- **WHEN** a maintainer runs the relevant package, build, or test check with missing or stale compiled playground assets, or with a stale generated TypeScript types module
- **THEN** the check fails with an actionable message naming the frontend rebuild command
- **AND** does not silently ship a playground shell that depends on source files outside the package or on a types module out of sync with the Python payload models
