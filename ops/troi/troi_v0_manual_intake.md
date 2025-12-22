# Troi v0: Manual Email Intake

## Overview

Troi v0 provides a **manual, operator-invoked** workflow for converting S3-stored raw emails into GitHub-issue-ready markdown. This approach adheres to Scotty governance:

- **No automation**: No daemons, cron jobs, or polling loops
- **No GitHub API calls**: Operator manually creates GitHub issues
- **No LLM classification**: Operator performs all triage and routing
- **Manual invocation only**: All operations are explicit and auditable
- **Small, reversible changes**: Each step is transparent and can be reviewed

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

### Save to File

```bash
python ops/troi/render_email.py \
  --bucket troi-mail-inbound-stardock \
  --key raw/2024-12-21T15:30:00Z-abc123 \
  --out issue-draft.md
```

This saves the markdown to `ops/troi/triaged/issue-draft.md` (relative to project root).

### Workflow Example

1. **Operator receives notification** (email, Slack, etc.) about new S3 object
2. **Operator runs render_email.py** to preview content:
   ```bash
   python ops/troi/render_email.py --bucket troi-mail-inbound-stardock --key raw/xyz
   ```
3. **Operator reviews output**, determines priority/category
4. **Operator creates GitHub issue** manually:
   - Copy markdown output
   - Create issue via GitHub UI or `gh issue create`
   - Apply appropriate labels (bug, feature, support, etc.)
   - Assign to team member if needed
5. **Operator saves triaged version** (optional):
   ```bash
   python ops/troi/render_email.py --bucket ... --key ... --out triaged-$(date +%Y%m%d-%H%M%S).md
   ```

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
- ✅ Optional file output under `ops/troi/triaged/` (gitignored)

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
