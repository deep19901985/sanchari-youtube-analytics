"""Simple local prerequisites check. Never prints secrets or environment values."""
from __future__ import annotations
import platform
import shutil
import subprocess
import sys


def main() -> int:
    print(f"Python: {sys.version.split()[0]} ({platform.system()})")
    py_ok = sys.version_info >= (3, 11)
    print(f"Python >= 3.11: {'PASS' if py_ok else 'FAIL'}")
    git = shutil.which("git")
    if git:
        version = subprocess.run([git, "--version"], capture_output=True, text=True, check=False)
        print("Git:", version.stdout.strip() or version.stderr.strip())
    else:
        print("Git: NOT FOUND. Install Git and restart terminal.")
    try:
        import pytest
        print("pytest:", pytest.__version__)
    except ImportError:
        print("pytest: NOT FOUND. Install dev dependencies.")
    return 0 if py_ok and git else 1


if __name__ == "__main__":
    raise SystemExit(main())
