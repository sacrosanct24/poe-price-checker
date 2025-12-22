# Troi: Manual Issue Intake System

## Overview

Troi is a **governance-compliant, manual email-to-issue intake system** designed to convert S3-stored emails into GitHub issues with full operator control and auditability.

## Components

### Documentation
- **[troi_v0_manual_intake.md](./troi_v0_manual_intake.md)** - Complete v0 specification, workflows, and governance compliance

### Tools
- **[render_email.py](./render_email.py)** - Manual email renderer (S3 → Markdown)

### Output Locations
- **GOVERNANCE:** All file outputs MUST use `/tmp/` or `~/.cache/troi/` only
- **No repo writes:** The script enforces this constraint and will exit with error if `--out` targets the repository

## Quick Start

1. **Install dependencies** (not in project requirements):
   ```bash
   uv pip install boto3 beautifulsoup4
   ```

2. **Configure AWS credentials** for S3 access:
   ```bash
   aws configure  # or use IAM role / env vars
   ```

3. **Render an email** from S3:
   ```bash
   python ops/troi/render_email.py \
     --bucket troi-mail-inbound-stardock \
     --key raw/2024-12-21T15:30:00Z-abc123
   ```

4. **Review output** and manually create GitHub issue

## Key Principles (Scotty Governance)

✅ **Manual Only**: No automation, daemons, or cron jobs
✅ **Operator Control**: Human triage for all decisions
✅ **Auditable**: Full provenance tracking (S3 key, metadata)
✅ **Reversible**: Small, transparent changes
✅ **No LLM Classification**: Operator performs all routing

## Workflow

```
S3 Email → render_email.py → Markdown → Operator Review → GitHub Issue
         (manual invocation)                           (manual creation)
```

## Example Usage

### Preview Email Content
```bash
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/xyz
```

### Save Draft for Review
```bash
# Save to /tmp (recommended)
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/xyz \
  --out /tmp/issue-draft-$(date +%Y%m%d-%H%M%S).md

# Or save to ~/.cache/troi/
mkdir -p ~/.cache/troi
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/xyz \
  --out ~/.cache/troi/issue-draft-$(date +%Y%m%d-%H%M%S).md
```

### Create GitHub Issue (WEB UI ONLY)

**CRITICAL: Issue creation is WEB UI ONLY. No GitHub CLI (`gh`) or API calls permitted.**

```bash
# Render markdown to stdout, copy to clipboard
python ops/troi/render_email.py --bucket ... --key ... | pbcopy

# Or save to temporary file for review
python ops/troi/render_email.py --bucket ... --key ... --out /tmp/issue-draft.md

# Then manually create GitHub issue via web UI:
# 1. Navigate to https://github.com/sacrosanct24/poe-price-checker/issues/new
# 2. Paste markdown content into issue body
# 3. Add title, labels, and triage notes
# 4. Submit issue manually
```

## Support

- **Documentation**: See [troi_v0_manual_intake.md](./troi_v0_manual_intake.md)
- **Governance**: Consult Scotty team for policy questions
- **Issues**: Label with `ops/troi` in GitHub

## Version History

- **v0** (2024-12): Initial manual intake implementation
  - S3 email download and parsing
  - HTML → text conversion
  - Markdown rendering with full provenance
  - Manual operator triage workflow
