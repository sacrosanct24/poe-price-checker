# Phase 2: Interface Boundaries (core / data_sources / UI)

## Purpose
Document the interface boundaries between `core/`, `data_sources/`, and the UI
layer so Phase 2 modernization work can add tests and documentation without
changing runtime behavior.

This phase does **not** introduce refactors, module moves, or UI changes.

## Boundary Map

### `core/` (domain + orchestration)
- **Responsibilities:** domain logic, orchestration, application services,
  configuration, and interface definitions.
- **Allowed imports:** `data_sources/` for adapters, stdlib, third-party libs.
- **Forbidden imports:** UI modules (`gui_qt/`), direct GUI widget usage.
- **Notes:** `core/interfaces.py` defines `IAppContext` to avoid direct UI
  coupling.

### `data_sources/` (adapters + external IO)
- **Responsibilities:** external APIs, file caches, parsing of external payloads,
  and adapter contracts.
- **Allowed imports:** `core/` constants/types where necessary, stdlib, requests.
- **Forbidden imports:** UI modules; direct AppContext wiring.
- **Notes:** Tests for adapters must be fixture-based and network-free.

### `gui_qt/` (UI layer)
- **Responsibilities:** presentation, user interaction, UI scheduling, and
  orchestration of UI-facing workflows.
- **Allowed imports:** `core/` services and `IAppContext` interfaces.
- **Forbidden imports:** `data_sources/` direct usage (use AppContext services).

## Composition Root (AppContext)
`core/app_context.py` is the **only** composition/wiring root. All dependency
construction and cross-layer wiring lives there. UI entry points receive a
fully constructed `AppContext` (or `IAppContext` interface) and do not
instantiate `data_sources/` clients directly.

## Adapter Contracts (Phase 2 tests)
Fixture-based contract tests validate adapter inputs/outputs without network
access:
- `tests/unit/data_sources/test_adapter_contracts.py`
- Contracts cover poe.ninja and RePoE adapters with fixture payloads.

## Dependency Direction Summary
- UI → core → data_sources
- data_sources → core (constants/types only)
- UI ⛔ data_sources (direct)

## Phase 2 Acceptance Criteria
- Boundaries are documented here.
- AppContext remains the only wiring root.
- Contract tests run without network access.
