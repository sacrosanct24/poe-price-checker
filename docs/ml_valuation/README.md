# ML Valuation Documentation

This directory contains design and specification documents for the ML-backed rare item valuation system.

## Documents

| Document | Status | Description |
|----------|--------|-------------|
| [ROADMAP.md](ROADMAP.md) | Living | Architecture and implementation roadmap |
| [GOALS.md](GOALS.md) | Complete | Success metrics and scope boundaries |
| DATA_CONTRACT.md | Pending | Feature schema and data requirements |
| [EVAL_PLAN.md](EVAL_PLAN.md) | Complete | Evaluation methodology and acceptance criteria |

## Current Status

**Phase 0: Feasibility Gate** — BLOCKED (see PHASE0_FEASIBILITY_REPORT.md).

Data collection restarted with a populated mod database; gate remains blocked until 2+ weeks of data are collected. Last recorded run: 2026-01-16T03:53:43+00:00.

## Data Collection

### Starting Collection

**Option 1: nohup (WSL2 without systemd)**

```bash
./scripts/start-ml-collector.sh
```

Starts collector in background. Logs to `~/.poe_price_checker/ml-collector.log`.

**Option 2: systemd (Linux with systemd)**

```bash
./scripts/setup-ml-collector.sh
```

Installs as a user service that starts on login and survives logout.

**Note:** WSL2 defaults to nohup mode. The collector survives terminal close but NOT machine restart. After restart, run `start-ml-collector.sh` again.

### Checking Status

```bash
./scripts/ml-collector-status.sh
```

Shows service status, recent logs, and database stats.

## Daily Feasibility Report

Run the report on demand:
```bash
./scripts/ml-feasibility-daily.py
```

Install a daily noon job (systemd user timer with cron fallback):
```bash
./scripts/install-ml-feasibility-timer.sh
```

Reports are written to `docs/ml_valuation/reports/feasibility_status_YYYY-MM-DD.md`.

### Stopping Collection

```bash
./scripts/ml-collector-stop.sh
```

### Manual Commands

```bash
# View live logs
journalctl --user -u poe-ml-collector -f

# Restart service
systemctl --user restart poe-ml-collector

# Disable service (won't start on login)
systemctl --user disable poe-ml-collector
```

### Collection Configuration

Edit `ml/collection/config.py` to change:
- `frequency_minutes`: Polling interval (default: 30)
- `base_types`: Item bases to collect
- `max_listings_per_base`: Listings per base per run (default: 100)
- `league`: Target league (default: Keepers)

After config changes, restart the service:
```bash
systemctl --user restart poe-ml-collector
```

## Feasibility Gate

After 2 weeks of collection, run the signal sanity check per EVAL_PLAN.md:
- Compare median prices with-affix vs without-affix
- Require 3+ affixes with statistically significant price correlation
- Document go/no-go decision before proceeding to Phase 1
