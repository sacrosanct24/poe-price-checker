#!/usr/bin/env python
"""
Build script for PoE Price Checker executables.

Usage:
    python build.py          # Build for current platform
    python build.py --clean  # Clean build artifacts first
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def clean_build():
    """Remove build artifacts."""
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Removing {dir_name}/...")
            shutil.rmtree(dir_path)
    print("Clean complete.")


def build():
    """Run PyInstaller build."""
    print(f"Building for {sys.platform}...")

    # Run PyInstaller
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', 'poe_price_checker.spec', '--noconfirm'],
        check=False
    )

    if result.returncode == 0:
        print("\nBuild successful!")
        print("Output: dist/PoEPriceChecker/")
        if sys.platform == 'win32':
            print("Executable: dist/PoEPriceChecker/PoEPriceChecker.exe")
        elif sys.platform == 'darwin':
            print("App bundle: dist/PoE Price Checker.app/")
        else:
            print("Executable: dist/PoEPriceChecker/PoEPriceChecker")
    else:
        print("\nBuild failed!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build PoE Price Checker executable")
    parser.add_argument('--clean', action='store_true', help="Clean build artifacts first")
    args = parser.parse_args()

    if args.clean:
        clean_build()

    build()


if __name__ == '__main__':
    main()
