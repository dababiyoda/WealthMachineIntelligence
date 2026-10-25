"""Export Docker/pip requirements from the single authored dependency list.

Run after editing pyproject.toml; --check refuses drift without writing files.
Python 3.11+ and the standard library are sufficient.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def render(project: Path) -> str:
    dependencies = tomllib.loads(project.read_text(encoding="utf-8"))["project"]["dependencies"]
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) and item.strip() and "\n" not in item and "\r" not in item
        for item in dependencies
    ):
        raise ValueError("project.dependencies must contain nonempty single-line requirement strings")
    return "# Generated from pyproject.toml; do not edit.\n# Refresh: python scripts/export_requirements.py\n" + "".join(
        item + "\n" for item in dependencies
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = render(ROOT / "pyproject.toml")
    destination = ROOT / "requirements.txt"
    if args.check:
        if not destination.is_file() or destination.read_text(encoding="utf-8") != expected:
            print("requirements.txt is stale; run python scripts/export_requirements.py")
            return 1
    else:
        destination.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
