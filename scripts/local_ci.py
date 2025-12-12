#!/usr/bin/env python
"""
Local CI runner - mirrors GitHub Actions CI checks.

Run this before pushing to catch issues locally:
    python scripts/local_ci.py              # Run all checks
    python scripts/local_ci.py --quick      # Skip tests, just lint + type check
    python scripts/local_ci.py --lint       # Only run linting
    python scripts/local_ci.py --test       # Only run tests
    python scripts/local_ci.py --security   # Only run bandit security scan
    python scripts/local_ci.py --security-full  # Full security: bandit (strict) + pip-audit
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    # Try to set console to UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Use ASCII alternatives for checkmarks on Windows if needed
PASS_MARK = "[PASS]"
FAIL_MARK = "[FAIL]"


def run_command(name: str, cmd: list[str], check: bool = True) -> bool:
    """Run a command and return success status."""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Running: {name}{RESET}")
    print(f"{BLUE}Command: {' '.join(cmd)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    try:
        result = subprocess.run(cmd, check=check)
        if result.returncode == 0:
            print(f"\n{GREEN}{PASS_MARK} {name} passed{RESET}")
            return True
        else:
            print(f"\n{RED}{FAIL_MARK} {name} failed (exit code {result.returncode}){RESET}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"\n{RED}{FAIL_MARK} {name} failed (exit code {e.returncode}){RESET}")
        return False
    except FileNotFoundError:
        print(f"\n{RED}{FAIL_MARK} {name} failed - command not found{RESET}")
        return False


def check_tool_installed(tool: str) -> bool:
    """Check if a tool is installed."""
    try:
        subprocess.run(
            [sys.executable, "-m", tool, "--version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_missing_tools():
    """Install missing CI tools."""
    tools = ["flake8", "mypy", "pytest", "bandit"]
    missing = [t for t in tools if not check_tool_installed(t)]

    if missing:
        print(f"{YELLOW}Installing missing tools: {', '.join(missing)}{RESET}")
        subprocess.run([
            sys.executable, "-m", "pip", "install", *missing,
            "types-requests", "pytest-qt", "pytest-cov", "pytest-timeout"
        ], check=True)


def run_flake8() -> bool:
    """Run flake8 linting."""
    return run_command(
        "Flake8 Lint",
        [sys.executable, "-m", "flake8",
         "core", "gui_qt", "data_sources", "tests",
         "--count", "--show-source", "--statistics"],
        check=False
    )


def run_mypy() -> bool:
    """Run mypy type checking."""
    return run_command(
        "Mypy Type Check",
        [sys.executable, "-m", "mypy",
         "--config-file=mypy.ini",
         "--install-types", "--non-interactive"],
        check=False
    )


def run_bandit(strict: bool = False) -> bool:
    """Run bandit security scan."""
    cmd = [
        sys.executable, "-m", "bandit",
        "-r", "core", "gui_qt", "data_sources",
    ]
    if strict:
        # Strict mode: fail on HIGH severity, report all
        cmd.extend(["--severity-level", "HIGH", "-f", "txt"])
    else:
        # Normal mode: report low and above
        cmd.extend(["-ll", "-ii"])

    return run_command("Bandit Security Scan", cmd, check=False)


def run_pip_audit() -> bool:
    """Run pip-audit dependency vulnerability scan."""
    return run_command(
        "Pip-Audit Dependency Scan",
        [sys.executable, "-m", "pip_audit",
         "-r", "requirements.txt", "--desc", "on"],
        check=False
    )


def run_security_tests() -> bool:
    """Run security-specific tests."""
    security_tests = Path("tests/security")
    if not security_tests.exists():
        print(f"{YELLOW}No security tests found at {security_tests}{RESET}")
        return True  # Not a failure if tests don't exist yet

    return run_command(
        "Security Tests",
        [sys.executable, "-m", "pytest", "tests/security/", "-v"],
        check=False
    )


def run_tests(quick: bool = False) -> bool:
    """Run pytest tests."""
    cmd = [
        sys.executable, "-m", "pytest", "tests/",
        "--ignore=tests/integration",
        "-v", "--tb=short"
    ]

    if quick:
        # Just run unit tests without coverage
        cmd.extend(["-m", "unit", "-q", "--ignore=tests/unit/gui_qt"])
    else:
        # Full test run with coverage
        cmd.extend([
            "--cov=core", "--cov=gui_qt",
            "--cov-report=term-missing",
            "--timeout=120"
        ])

    return run_command("Pytest", cmd, check=False)


def main():
    parser = argparse.ArgumentParser(
        description="Run local CI checks before pushing"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: skip tests, just lint + type check"
    )
    parser.add_argument(
        "--lint", action="store_true",
        help="Only run linting (flake8)"
    )
    parser.add_argument(
        "--type", action="store_true",
        help="Only run type checking (mypy)"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Only run tests"
    )
    parser.add_argument(
        "--security", action="store_true",
        help="Only run security scan (bandit)"
    )
    parser.add_argument(
        "--security-full", action="store_true",
        help="Full security scan: bandit (strict) + pip-audit + security tests"
    )
    parser.add_argument(
        "--no-install", action="store_true",
        help="Don't auto-install missing tools"
    )

    args = parser.parse_args()

    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print(f"{BOLD}Local CI Runner{RESET}")
    print(f"Project: {project_root}")
    print(f"Python: {sys.executable}")

    # Install missing tools unless disabled
    if not args.no_install:
        install_missing_tools()

    results = {}

    # Determine which checks to run
    run_all = not (args.lint or args.type or args.test or args.security or args.security_full)

    if args.lint or run_all:
        results["flake8"] = run_flake8()

    if args.type or run_all:
        results["mypy"] = run_mypy()

    if args.security_full:
        # Full security scan: strict bandit + pip-audit + security tests
        results["bandit"] = run_bandit(strict=True)
        results["pip-audit"] = run_pip_audit()
        results["security-tests"] = run_security_tests()
    elif args.security or run_all:
        results["bandit"] = run_bandit(strict=False)

    if args.test or (run_all and not args.quick):
        results["pytest"] = run_tests(quick=args.quick)

    # Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}CI Results Summary{RESET}")
    print(f"{'='*60}")

    all_passed = True
    for name, passed in results.items():
        status = f"{GREEN}{PASS_MARK}{RESET}" if passed else f"{RED}{FAIL_MARK}{RESET}"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print(f"{'='*60}")
    if all_passed:
        print(f"{GREEN}{BOLD}All checks passed! Safe to push.{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}Some checks failed. Fix issues before pushing.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
