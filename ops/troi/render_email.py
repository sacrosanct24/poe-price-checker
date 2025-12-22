#!/usr/bin/env python3
"""
Troi v0: Manual Email Renderer

Downloads RFC-822 email from S3 and converts to GitHub-issue-ready markdown.
Manual invocation only - no automation.

Usage:
    python ops/troi/render_email.py --bucket BUCKET --key KEY [--out FILE]

Requirements:
    pip install boto3 beautifulsoup4
"""

import argparse
import email
import sys
from datetime import datetime
from email import policy
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

try:
    import boto3
except ImportError:
    print("ERROR: boto3 not installed. Run: uv pip install boto3 beautifulsoup4", file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: uv pip install boto3 beautifulsoup4", file=sys.stderr)
    sys.exit(1)


def download_email_from_s3(bucket: str, key: str) -> bytes:
    """Download raw email from S3."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        print(f"ERROR: Failed to download s3://{bucket}/{key}: {e}", file=sys.stderr)
        sys.exit(1)


def parse_email(raw_email: bytes) -> EmailMessage:
    """Parse RFC-822 email."""
    return email.message_from_bytes(raw_email, policy=policy.default)


def extract_body(msg: EmailMessage) -> tuple[str, str]:
    """
    Extract email body, preferring HTML over plain text.

    Returns:
        tuple: (content, content_type) where content_type is 'html' or 'plain'
    """
    html_content = None
    plain_content = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            try:
                if content_type == "text/plain" and plain_content is None:
                    plain_content = part.get_content()
                elif content_type == "text/html" and html_content is None:
                    html_content = part.get_content()
            except Exception:
                # Skip parts that can't be decoded
                continue
    else:
        # Not multipart - single content type
        content_type = msg.get_content_type()
        try:
            if content_type == "text/html":
                html_content = msg.get_content()
            elif content_type == "text/plain":
                plain_content = msg.get_content()
        except Exception:
            pass

    # Prefer HTML, fall back to plain
    if html_content:
        return html_content, 'html'
    elif plain_content:
        return plain_content, 'plain'
    else:
        return "[No readable content found]", 'plain'


def html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text and clean up whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text


def render_markdown(msg: EmailMessage, bucket: str, key: str) -> str:
    """Render email as GitHub-issue-ready markdown."""

    # Extract metadata
    subject = msg.get('Subject', '[No Subject]')
    from_addr = msg.get('From', '[Unknown]')
    to_addr = msg.get('To', '[Unknown]')
    date = msg.get('Date', '[Unknown]')
    message_id = msg.get('Message-ID', '[Unknown]')

    # Extract body
    body, content_type = extract_body(msg)

    # Convert HTML to text if needed
    if content_type == 'html':
        body = html_to_text(body)

    # Build markdown output
    output = []
    output.append("<!-- Troi v0 Manual Intake -->")
    output.append("<!-- DO NOT AUTOMATE: This issue was manually created by operator -->")
    output.append("")
    output.append("## Email Metadata")
    output.append("")
    output.append(f"**Subject**: {subject}")
    output.append(f"**From**: {from_addr}")
    output.append(f"**To**: {to_addr}")
    output.append(f"**Date**: {date}")
    output.append(f"**Message-ID**: `{message_id}`")
    output.append("")
    output.append("## Provenance")
    output.append("")
    output.append(f"**S3 Bucket**: `{bucket}`")
    output.append(f"**S3 Key**: `{key}`")
    output.append(f"**Processed**: {datetime.utcnow().isoformat()}Z")
    output.append("")
    output.append("---")
    output.append("")
    output.append("## Email Content")
    output.append("")
    output.append(body)
    output.append("")
    output.append("---")
    output.append("")
    output.append("## Operator Triage Notes")
    output.append("")
    output.append("<!-- Operator: Add triage notes, labels, assignments here -->")
    output.append("")
    output.append("- **Priority**: [Low/Medium/High/Critical]")
    output.append("- **Category**: [Bug/Feature/Support/Question/Other]")
    output.append("- **Action Required**: [Describe next steps]")
    output.append("")

    return '\n'.join(output)


def get_repo_root() -> Optional[Path]:
    """
    Detect git repository root.

    Returns None if not in a git repo, otherwise returns the repo root path.
    """
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
        return None
    except Exception:
        # Fallback: traverse up looking for .git directory
        current = Path(__file__).resolve().parent
        for parent in [current] + list(current.parents):
            if (parent / '.git').exists():
                return parent
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Troi v0: Convert S3-stored email to GitHub-issue-ready markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Print to stdout
  python ops/troi/render_email.py --bucket troi-mail-inbound-stardock --key raw/abc123

  # Save to file (outside repo)
  python ops/troi/render_email.py --bucket troi-mail-inbound-stardock --key raw/abc123 --out /tmp/issue.md
  python ops/troi/render_email.py --bucket troi-mail-inbound-stardock --key raw/abc123 --out ~/.cache/troi/issue.md

Requirements:
  boto3, beautifulsoup4 (install via: uv pip install boto3 beautifulsoup4)

AWS Credentials:
  Configure via ~/.aws/credentials, environment variables, or IAM role

GOVERNANCE: --out must NOT write inside the repository working tree.
            Use /tmp/ or ~/.cache/troi/ for output files.
        """
    )

    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--key', required=True, help='S3 object key')
    parser.add_argument('--out', help='Output file (absolute path, MUST be outside repo). If omitted, prints to stdout')

    args = parser.parse_args()

    # Download email from S3
    print(f"Downloading s3://{args.bucket}/{args.key} ...", file=sys.stderr)
    raw_email = download_email_from_s3(args.bucket, args.key)

    # Parse email
    print("Parsing email...", file=sys.stderr)
    msg = parse_email(raw_email)

    # Render markdown
    print("Rendering markdown...", file=sys.stderr)
    markdown = render_markdown(msg, args.bucket, args.key)

    # Output
    if args.out:
        output_path = Path(args.out).resolve()

        # GOVERNANCE: Refuse to write inside repository working tree
        repo_root = get_repo_root()
        if repo_root is not None:
            try:
                # Check if output_path is inside repo_root
                output_path.relative_to(repo_root)
                # If we get here, output_path IS inside repo_root - reject it
                print("", file=sys.stderr)
                print("❌ ERROR: Output path is inside repository working tree", file=sys.stderr)
                print(f"   Repository root: {repo_root}", file=sys.stderr)
                print(f"   Requested output: {output_path}", file=sys.stderr)
                print("", file=sys.stderr)
                print("GOVERNANCE VIOLATION: render_email.py must not write to repo.", file=sys.stderr)
                print("", file=sys.stderr)
                print("Recommended output locations:", file=sys.stderr)
                print("  - /tmp/issue-draft.md", file=sys.stderr)
                print("  - ~/.cache/troi/issue-draft.md", file=sys.stderr)
                print("", file=sys.stderr)
                sys.exit(1)
            except ValueError:
                # output_path is NOT relative to repo_root - this is OK
                pass

        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output
        output_path.write_text(markdown, encoding='utf-8')
        print(f"✅ Saved to: {output_path}", file=sys.stderr)
    else:
        # Print to stdout
        print("", file=sys.stderr)  # Blank line before output
        print(markdown)
        print("", file=sys.stderr)  # Blank line after output
        print("✅ Markdown rendered successfully", file=sys.stderr)


if __name__ == '__main__':
    main()
