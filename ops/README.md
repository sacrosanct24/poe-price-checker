# Ops — Repo-Local Execution Support

**Canonical governance source:** `devcenter-system/governance/ROLES.md`

## Purpose

The `ops/` directory in poe-price-checker contains **repo-local execution support only**. This directory does NOT claim canonical governance authority.

All canonical governance lives in:
- **Studio governance:** `devcenter-system/governance/`
- **Tool-specific governance:** `python-prime/ops/agents/cline/`

## Structure

- **[governance/](./governance/)** - Pointer to canonical governance in devcenter-system
- **[scotty/](./scotty/)** - Repo-local Scotty execution support (pointer to canonical charter)
- **[orchestrator/](./orchestrator/)** - Repo-local orchestrator support (pointers to canonical templates)
- **[agents/cline/](./agents/cline/)** - Repo-local Cline support (pointers to python-prime governance)
- **[inventory/](./inventory/)** - Pointer to canonical inventory in devcenter-system
- **[troi/](./troi/)** - Pointer to troi-system repository
- **[repo_overrides.md](./repo_overrides.md)** - Repo-local execution configuration

## Canonical References

All paths in this directory are **repo-local to poe-price-checker** unless explicitly stated otherwise.

Canonical governance artifacts live in:
- **Roles & operating model:** `devcenter-system/governance/ROLES.md`
- **Scotty charter:** `devcenter-system/governance/agents/scotty/CHARTER.md`
- **Task templates:** `devcenter-system/governance/templates/`
- **Cline tool governance:** `python-prime/ops/agents/cline/`

## Compliance

This repository follows the Studio Governance Model defined in `devcenter-system/governance/ROLES.md`. All agents operating in this repo are bound by that canonical governance unless explicitly overridden by the Human Owner (Todd).
