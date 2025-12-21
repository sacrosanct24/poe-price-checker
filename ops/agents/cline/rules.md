# Cline Execution Rules — Canonical (Python-Prime)

These rules govern all execution agents operating in this repository.

## Authority
- Python-Prime is a golden reference repository.
- These rules are human-owned governance artifacts.
- Agents may not modify these rules or workflows.

## Scope
- Default allowed modification paths:
  - src/
  - tests/

## Hard Constraints
- Do NOT modify unless explicitly instructed:
  - pyproject.toml
  - uv.lock
  - .pre-commit-config.yaml
  - check.sh
  - CI / workflows
  - tooling or formatting rules
- Do NOT introduce new dependencies.
- Do NOT refactor unrelated code.
- Do NOT add abstractions or "future-proofing."

## Quality Gates
- You must run `./check.sh` before presenting results.
- If checks fail, fix code — never rules.

## Ambiguity
- If instructions are unclear or conflicting:
  - STOP
  - Ask for clarification
  - Do not guess

## Output
- Provide minimal, reviewable diffs.
- Provide a 2–3 sentence summary only.
