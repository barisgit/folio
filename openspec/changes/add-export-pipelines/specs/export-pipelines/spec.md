## ADDED Requirements

### Requirement: Dependency-aware export planning
Folio SHALL plan requested export targets as a dependency graph before executing export steps.

#### Scenario: Requested target with dependencies
- **WHEN** a user builds a target whose preset depends on another preset
- **THEN** Folio includes the dependency preset in the build plan
- **AND** executes the dependency before the requested target

#### Scenario: Transitive dependencies
- **WHEN** target `pdf` depends on `1080p` and `1080p` depends on `svg`
- **THEN** Folio plans `svg`, then `1080p`, then `pdf`
- **AND** does not require the user to request dependency targets explicitly

#### Scenario: Deterministic plan ordering
- **WHEN** multiple requested targets share dependencies
- **THEN** Folio executes each dependency once per document/page participation set
- **AND** orders execution deterministically by document order, dependency order, page order, and preset declaration order

### Requirement: Typed pipeline compatibility
Folio SHALL validate export pipeline edges using built-in artifact types and handler capabilities.

#### Scenario: Supported source route
- **WHEN** `pdf(source="1080p")` declares a source PNG preset supported by the raster PDF backend
- **THEN** Folio accepts the graph
- **AND** passes the PNG page artifacts to the PDF step
- **AND** keeps the requested target name as `pdf`

#### Scenario: Unsupported source route
- **WHEN** a preset declares a source whose artifact type is not accepted by that preset's handler
- **THEN** Folio rejects the build plan
- **AND** reports the source preset, target preset, and unsupported artifact types

#### Scenario: Source compatibility matrix
- **WHEN** Folio validates built-in preset sources
- **THEN** `svg` and `idml` reject explicit sources
- **AND** `png` accepts page-scoped SVG sources
- **AND** `pdf` accepts page-scoped PNG sources for raster PDF output
- **AND** unsupported SVG-sourced vector PDF routes remain unavailable until a vector PDF backend exists

#### Scenario: Unknown source preset
- **WHEN** a preset declares `source="missing"`
- **THEN** Folio rejects the document or build plan
- **AND** includes the missing source name in the diagnostic

### Requirement: Cycle detection
Folio SHALL reject export pipeline graphs with dependency cycles.

#### Scenario: Direct cycle
- **WHEN** preset `a` depends on `b` and preset `b` depends on `a`
- **THEN** Folio reports a validation error
- **AND** includes the cycle path in the diagnostic

#### Scenario: Transitive cycle
- **WHEN** preset `a` depends on `b`, `b` depends on `c`, and `c` depends on `a`
- **THEN** Folio reports a validation error
- **AND** does not attempt to execute any export step in the cycle

### Requirement: Intermediate artifact reuse
Folio SHALL reuse intermediate artifacts produced while executing a build plan.

#### Scenario: Shared dependency
- **WHEN** two requested targets depend on the same rendered SVG page artifact
- **THEN** Folio renders that SVG page once for the build plan
- **AND** reuses it for both downstream targets

#### Scenario: Dependency not explicitly requested
- **WHEN** `folio build pdf` needs an intermediate PNG source
- **THEN** Folio may produce the PNG as an intermediate artifact
- **AND** does not write the PNG to the public output directory unless that PNG target was also requested

#### Scenario: Dependency explicitly requested
- **WHEN** `folio build 1080p pdf` builds a PDF sourced from `1080p`
- **THEN** Folio writes the `1080p` PNG output because it was explicitly requested
- **AND** reuses the same PNG artifact for the PDF step

### Requirement: Pipeline failure propagation
Folio SHALL fail the requested build when a dependency or terminal pipeline step fails.

#### Scenario: Dependency failure
- **WHEN** a PNG dependency fails to rasterize while building a PDF target
- **THEN** Folio reports a build/render error for the requested PDF target
- **AND** includes the failing dependency step in the diagnostic

#### Scenario: Terminal failure
- **WHEN** all dependencies succeed but the terminal PDF assembly fails
- **THEN** Folio reports a build/render error for the PDF target
- **AND** does not emit a misleading terminal artifact
