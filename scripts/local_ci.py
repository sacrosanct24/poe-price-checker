#!/usr/bin/env python
"""
Local CI runner - mirrors GitHub Actions CI checks.

Run this before pushing to catch issues locally:
    python scripts/local_ci.py              # Standard checks (lint, type, bandit, tests)
    python scripts/local_ci.py --full       # FULL CI mirror (all checks + integration)
    python scripts/local_ci.py --quick      # Skip tests, just lint + type check
    python scripts/local_ci.py --lint       # Only run linting
    python scripts/local_ci.py --test       # Only run unit tests
    python scripts/local_ci.py --integration  # Only run integration tests
    python scripts/local_ci.py --no-qt      # Skip Qt/GUI tests (faster)
    python scripts/local_ci.py --security   # Only run bandit security scan
    python scripts/local_ci.py --security-full  # Full security: bandit (strict) + pip-audit
    python scripts/local_ci.py --complexity # Run radon code complexity analysis
    python scripts/local_ci.py --coverage   # Run tests with coverage + HTML report

Recommended before pushing:
    python scripts/local_ci.py --full       # Catches most CI failures locally
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


def run_tests(quick: bool = False, include_qt: bool = True) -> bool:
    """Run pytest tests."""
    # Set Qt offscreen mode for headless testing
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"

    cmd = [
        sys.executable, "-m", "pytest", "tests/",
        "--ignore=tests/integration",
        "-v", "--tb=short"
    ]

    if quick:
        # Just run unit tests without coverage, skip Qt tests
        cmd.extend(["-m", "unit", "-q", "--ignore=tests/unit/gui_qt"])
    else:
        # Full test run with coverage
        cmd.extend([
            "--cov=core", "--cov=gui_qt",
            "--cov-report=term-missing",
            "--timeout=120"
        ])
        if not include_qt:
            cmd.extend(["--ignore=tests/unit/gui_qt", "--ignore=tests/test_shortcuts.py"])

    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Running: Pytest{RESET}")
    print(f"{BLUE}Command: {' '.join(cmd)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    try:
        result = subprocess.run(cmd, check=False, env=env)
        if result.returncode == 0:
            print(f"\n{GREEN}{PASS_MARK} Pytest passed{RESET}")
            return True
        else:
            print(f"\n{RED}{FAIL_MARK} Pytest failed (exit code {result.returncode}){RESET}")
            return False
    except Exception as e:
        print(f"\n{RED}{FAIL_MARK} Pytest failed: {e}{RESET}")
        return False


def run_integration_tests() -> bool:
    """Run integration tests."""
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    cmd = [
        sys.executable, "-m", "pytest", "tests/integration/",
        "-v", "--timeout=300",
        "--ignore=tests/integration/test_ai_connectivity.py"  # Skip flaky external API tests
    ]

    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Running: Integration Tests{RESET}")
    print(f"{BLUE}Command: {' '.join(cmd)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    try:
        result = subprocess.run(cmd, check=False, env=env)
        if result.returncode == 0:
            print(f"\n{GREEN}{PASS_MARK} Integration tests passed{RESET}")
            return True
        else:
            print(f"\n{RED}{FAIL_MARK} Integration tests failed (exit code {result.returncode}){RESET}")
            return False
    except Exception as e:
        print(f"\n{RED}{FAIL_MARK} Integration tests failed: {e}{RESET}")
        return False


def run_complexity() -> bool:
    """Run radon complexity analysis."""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Running: Code Complexity (radon){RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    try:
        # Run radon for overall complexity
        result = subprocess.run(
            [sys.executable, "-m", "radon", "cc",
             "core", "gui_qt", "data_sources",
             "-a", "-s", "--total-average"],
            check=False
        )

        # Check for high complexity functions (grade C or worse)
        check_result = subprocess.run(
            [sys.executable, "-m", "radon", "cc",
             "core", "gui_qt", "data_sources",
             "-a", "-nc", "--min", "C"],
            capture_output=True,
            text=True
        )

        high_complexity = check_result.stdout.strip()
        if high_complexity:
            line_count = len([l for l in high_complexity.splitlines() if l.strip()])
            print(f"\n{YELLOW}Warning: {line_count} functions with complexity >= C (11-20){RESET}")
            print(high_complexity)

        print(f"\n{GREEN}{PASS_MARK} Code Complexity analysis complete{RESET}")
        return True
    except FileNotFoundError:
        print(f"\n{YELLOW}radon not installed. Install with: pip install radon{RESET}")
        return True  # Don't fail if radon isn't installed


def run_coverage_check() -> bool:
    """Run tests with coverage and check against threshold."""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Running: Coverage Check{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # Check if .coveragerc exists
    coveragerc = Path(".coveragerc")
    if not coveragerc.exists():
        print(f"{YELLOW}No .coveragerc found. Using default settings.{RESET}")

    cmd = [
        sys.executable, "-m", "pytest", "tests/",
        "--ignore=tests/integration",
        "--cov=core", "--cov=gui_qt", "--cov=data_sources",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-q", "--timeout=120"
    ]

    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        print(f"\n{GREEN}{PASS_MARK} Coverage check passed{RESET}")
        print(f"HTML report: htmlcov/index.html")
        return True
    else:
        print(f"\n{RED}{FAIL_MARK} Coverage check failed{RESET}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run local CI checks before pushing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/local_ci.py              # Standard checks (lint, type, bandit, unit tests)
  python scripts/local_ci.py --full       # Full CI mirror (all checks + integration tests)
  python scripts/local_ci.py --quick      # Fast check (lint + type only)
  python scripts/local_ci.py --test       # Only run unit tests
  python scripts/local_ci.py --integration  # Only run integration tests
  python scripts/local_ci.py --coverage   # Tests with coverage report
        """
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Full CI mirror: lint, type, bandit, unit tests, integration tests, complexity"
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
        help="Only run unit tests"
    )
    parser.add_argument(
        "--integration", action="store_true",
        help="Only run integration tests"
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
        "--complexity", action="store_true",
        help="Run code complexity analysis (radon)"
    )
    parser.add_argument(
        "--coverage", action="store_true",
        help="Run tests with coverage check and HTML report"
    )
    parser.add_argument(
        "--no-install", action="store_true",
        help="Don't auto-install missing tools"
    )
    parser.add_argument(
        "--no-qt", action="store_true",
        help="Skip Qt/GUI tests (faster, matches CI unit-only job)"
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
    specific_check = (args.lint or args.type or args.test or args.security
                      or args.security_full or args.complexity or args.coverage
                      or args.integration)
    run_all = not specific_check
    run_full = args.full

    # Flake8 linting
    if args.lint or run_all or run_full:
        results["flake8"] = run_flake8()

    # Mypy type checking
    if args.type or run_all or run_full:
        results["mypy"] = run_mypy()

    # Security checks
    if args.security_full:
        # Full security scan: strict bandit + pip-audit + security tests
        results["bandit"] = run_bandit(strict=True)
        results["pip-audit"] = run_pip_audit()
        results["security-tests"] = run_security_tests()
    elif args.security or run_all or run_full:
        results["bandit"] = run_bandit(strict=False)

    # Complexity analysis (only in full mode or explicitly requested)
    if args.complexity or run_full:
        results["complexity"] = run_complexity()

    # Tests
    if args.coverage:
        results["coverage"] = run_coverage_check()
    elif args.test:
        results["pytest"] = run_tests(quick=False, include_qt=not args.no_qt)
    elif (run_all or run_full) and not args.quick:
        results["pytest"] = run_tests(quick=False, include_qt=not args.no_qt)

    # Integration tests (only in full mode or explicitly requested)
    if args.integration or run_full:
        results["integration"] = run_integration_tests()

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
