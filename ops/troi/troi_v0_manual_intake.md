# Troi v0: Manual Email Intake

## Overview

Troi v0 provides a **manual, operator-invoked** workflow for converting S3-stored raw emails into GitHub-issue-ready markdown. This approach adheres to Scotty governance:

- **No automation**: No daemons, cron jobs, or polling loops
- **No GitHub API calls**: Operator manually creates GitHub issues
- **No LLM classification**: Operator performs all triage and routing
- **Manual invocation only**: All operations are explicit and auditable
- **Small, reversible changes**: Each step is transparent and can be reviewed

## Inputs

- **S3 bucket:** `troi-mail-inbound-stardock`
- **Prefix:** `raw/`
- **Object:** raw RFC-822 message (as delivered by SES Mail Manager)

## Architecture

```
S3 Bucket (troi-mail-inbound-stardock)
  └── raw/<key>  (RFC-822 email object)
        ↓
   [Operator invokes render_email.py]
        ↓
   Markdown output (stdout or file)
        ↓
   [Operator reviews, triages, creates GitHub issue]
```

## Prerequisites

Install required dependencies (not in project requirements by default):

```bash
# Using uv (recommended)
uv pip install boto3 beautifulsoup4

# Or using pip
pip install boto3 beautifulsoup4
```

**AWS Credentials**: Ensure AWS credentials are configured for S3 access:
- Via `~/.aws/credentials`
- Via environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Via IAM role (if running on EC2/ECS)

## Usage

### Basic Usage (stdout)

```bash
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/2024-12-21T15:30:00Z-abc123
```

This prints GitHub-issue-ready markdown to stdout, including:
- Email metadata (Subject, From, Date, Message-ID, To)
- S3 provenance (bucket, key)
- Email body (HTML → text or plain text)

### Save to File (Outside Repo)

**GOVERNANCE: Output files MUST be saved outside the repository working tree.**

```bash
# Save to /tmp (recommended)
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/2024-12-21T15:30:00Z-abc123 \
  --out /tmp/issue-draft.md

# Or save to ~/.cache/troi/
mkdir -p ~/.cache/troi
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/2024-12-21T15:30:00Z-abc123 \
  --out ~/.cache/troi/issue-draft.md
```

The script will **refuse to write inside the repository** and exit with an error if `--out` points to a repo path.

### Workflow Example

**CRITICAL: GitHub issue creation is WEB UI ONLY. No GitHub CLI (`gh`) or API calls permitted.**

1. **Operator receives notification** (email, Slack, etc.) about new S3 object
2. **Operator runs render_email.py** to preview content:
   ```bash
   python ops/troi/render_email.py --bucket troi-mail-inbound-stardock --key raw/xyz
   ```
3. **Operator reviews output**, determines priority/category
4. **Operator creates GitHub issue manually via GitHub web UI**:
   - Copy markdown output to clipboard: `python ops/troi/render_email.py --bucket ... --key ... | pbcopy`
   - Navigate to https://github.com/sacrosanct24/poe-price-checker/issues/new
   - Paste markdown content into issue body
   - Add title, apply appropriate labels (bug, feature, support, etc.)
   - Assign to team member if needed
   - Submit issue manually
5. **Operator saves triaged version** (optional, outside repo):
   ```bash
   python ops/troi/render_email.py --bucket ... --key ... --out /tmp/triaged-$(date +%Y%m%d-%H%M%S).md
   ```

## Required Metadata (Preserve in Issue)

- S3 bucket name
- S3 object key
- `Message-ID`
- `Date`
- `From`
- `Subject`

## GitHub Issue Template

**Title:** `Troi Intake: <Subject>`

**Body:**

```
## Source
- S3 bucket: troi-mail-inbound-stardock
- S3 key: <raw/...>

## Message Metadata
- Message-ID: <...>
- Date: <...>
- From: <...>
- Subject: <...>

## Extracted Content
<plain text body or summarized content>

## Notes
- Content type: <text/plain | text/html | mixed>
- Operator: <name or handle>
```

## Done Checklist

- [ ] Issue created manually in GitHub.
- [ ] Issue contains S3 bucket and object key.
- [ ] Issue contains Message-ID, Date, From, Subject.
- [ ] Body content copied (or summarized if HTML-only).
- [ ] Any ambiguity or missing data is noted in the issue.

## Non-Goals

Troi v0 explicitly **does not** include:

- Automatic issue creation (via GitHub CLI, API, or any automation)
- Background ingestion or polling (no daemons, no Lambda, no cron jobs)
- Email-to-repo writes (no commits triggered by email)
- LLM-based classification or summarization (manual operator decision only)
- Data enrichment beyond the email content and required metadata

## Email Processing Details

### Content Selection
- Prefers `text/html` if present in multipart email
- Falls back to `text/plain` if no HTML
- Converts HTML to readable plain text using BeautifulSoup

### Encoding Support
- Handles `quoted-printable` and `base64` transfer encodings
- Converts all content to UTF-8
- Preserves special characters and international text

### Provenance Tracking
Every rendered email includes:
- **Subject**: Original email subject line
- **From**: Sender email address
- **Date**: Original send timestamp
- **Message-ID**: Unique email identifier
- **To**: Recipient email address(es)
- **S3 Location**: Bucket and key for audit trail

## Governance Compliance

### Manual Operation
- ✅ No automated loops or background processes
- ✅ Each invocation is explicit and logged
- ✅ Operator maintains full control over triage decisions

### Security
- ✅ S3 access requires valid AWS credentials
- ✅ No persistent storage (stdout by default)
- ✅ Optional file output to `/tmp/` or `~/.cache/troi/` only (no repo writes)
- ✅ Script enforces repo write protection (exits with error if `--out` targets repo)

### Auditability
- ✅ S3 object key preserved in output
- ✅ Original email metadata retained
- ✅ All operations are traceable

## Future Evolution

Troi v0 is intentionally minimal. Future versions may add:
- **Troi v1**: Pre-approved automation for simple cases (e.g., auto-label by keyword)
- **Troi v2**: LLM-assisted classification with human-in-the-loop
- **Troi v3**: Full workflow orchestration with governance guardrails

All future versions must receive Scotty approval and maintain auditability.

## Runbook (Failure Modes and Checks)

If mail is missing or not visible in S3, check the following in order:

- **MX records**: Confirm DNS MX for `stardock.tools` routes to SES Mail Manager.
- **Ingress endpoint**: Validate the SES inbound endpoint for `troi@stardock.tools` is active.
- **Traffic policy**: Ensure the inbound traffic policy allows the recipient and domain.
- **Rule set**: Confirm the rule set writes to `troi-mail-inbound-stardock` under `raw/`.
- **Object ownership**: Bucket should be set to "Bucket owner preferred" to avoid ACL access issues.
- **Bucket policy**: Ensure SES Mail Manager has scoped `s3:PutObject` and `s3:PutObjectAcl` to `raw/*` only.
- **IAM role permissions**: Verify the SES Mail Manager service role has `s3:PutObject` and `s3:PutObjectAcl` permissions scoped to the correct bucket and prefix.

If objects exist but are not readable:

- **Object ownership**: Confirm new objects are owned by the bucket owner.
- **Bucket policy**: Verify no explicit denies and the policy references the correct bucket and prefix.

## Permissions Posture

- **Bucket ownership: "Bucket owner preferred"**
  - Ensures the bucket owner can read inbound objects without ACL conflicts.
  - Avoids cross-account ownership ambiguity from SES delivery.
  - Prevents access control issues when operator downloads objects.

- **Scoped bucket policy principal**
  - SES Mail Manager service principal is scoped to the specific AWS account and region.
  - Prevents unauthorized mail delivery from other accounts or regions.
  - Enforces that only the designated SES endpoint can write to the bucket.

- **PutObject and PutObjectAcl only**
  - `s3:PutObject`: Allows SES to write email objects to S3.
  - `s3:PutObjectAcl`: Required by SES Mail Manager to set object ownership correctly.
  - No read, delete, or list permissions granted to SES (write-only, inbound only).
  - Operator reads objects via bucket owner permissions, not SES permissions.

- **Prefix restriction to `raw/*` only**
  - SES writes are confined to the `raw/` prefix.
  - Prevents SES from writing to other prefixes (e.g., `processed/`, `archive/`).
  - Isolates inbound mail from any future processing or storage zones.

- **Must not be broadened**
  - No public access.
  - No wildcard principals (`*` or `arn:aws:iam::*`).
  - No `s3:*` on the bucket (grants too much authority).
  - No write access outside `raw/`.
  - No delete permissions for SES delivery (no `s3:DeleteObject`).

## Troubleshooting

### "No credentials" error
Ensure AWS credentials are configured. Test with:
```bash
aws s3 ls s3://troi-mail-inbound-stardock/raw/ --profile <your-profile>
```

### "Module not found" error
Install dependencies:
```bash
uv pip install boto3 beautifulsoup4
```

### HTML not rendering correctly
The script uses BeautifulSoup's `get_text()` for simple HTML → text conversion. For complex HTML, consider saving to file and reviewing in browser.

## Support

For questions or issues with Troi v0:
1. Review this documentation
2. Check `ops/troi/render_email.py` source code
3. Consult with Scotty governance team
4. Create a GitHub issue with label `ops/troi`
