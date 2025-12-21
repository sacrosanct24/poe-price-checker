# Ops Governance README

## Purpose
The ops/ directory exists to provide a canonical, reusable governance baseline for Python repositories. It defines the minimum safe rules, templates, and roles that keep work predictable, bounded, and auditable. It prevents drift by making governance explicit and portable. If it isn’t declared, it doesn’t exist.

## Canonical Baseline Artifacts
- `ops/scotty/CHARTER.md` — Defines the read-only governance and planning role, including non-negotiable constraints and escalation rules.
- `ops/orchestrator/task_template.md` — Defines the required structure for tasks, including scope boundaries, proof gates, and rollback expectations.
- `ops/orchestrator/ci_failure_bundle_template.md` — Defines the required schema for CI failure intake, classification, and signal quality.

These artifacts define the minimum safe governance. Downstream repos may copy and extend them. Downstream repos must not weaken, contradict, or bypass them.

## Customizable / Repo-Specific Artifacts
Downstream repos may define and customize:
- Allowed modification paths
- Required local commands (for proofs and gates)
- CI workflow names and step mappings
- Agent-specific integrations (IDE tooling, local assistants)

These artifacts do not belong in Python Prime’s baseline. They are expected to diverge per repo and must live outside the canonical baseline.

## Agent Ownership Model
- Scotty: owns governance rules and templates; operates read-only as planner and auditor.
- Execution Agent: performs task execution; rules and workflows are repo-specific.
- Orchestrator Owner: grants approvals, resolves conflicts, and handles escalations.
- Troi (if referenced): owns fleet and environment awareness; read-only input to Scotty.

## Extension Rules
- Downstream repos may extend governance but not weaken it.
- New gates may be added; baseline gates may not be removed.
- Repo-specific rules must live outside the canonical baseline.
- If it isn’t declared, it doesn’t exist.

## Orchestrator Template Usage
- [ ] All tasks are authored from `ops/orchestrator/task_template.md`.
- [ ] CI failures are captured with `ops/orchestrator/ci_failure_bundle_template.md`.
- [ ] Work is not authorized until templates are present and used.

Note: This checklist is a minimum requirement and does not replace repo-specific gates.

## Inventory
Repository-specific inventory lives in `ops/inventory/README.md`.

## Warnings / Anti-Patterns
- Baking tool-specific workflows into baseline governance.
- Hard-coding repo layouts or command assumptions into templates.
- Treating execution agents as planners or governors.
- Allowing governance to drift silently across repos.
