#!/usr/bin/env python3
"""Extracts the '## Unreleased' section of a Keep-a-Changelog-style
CHANGELOG.md as a GitHub release body, and optionally bumps it into a
dated version section for a real release.
"""

import argparse
import datetime
import sys
from pathlib import Path

UNRELEASED_HEADING = "## Unreleased"
SCAFFOLD_SUBHEADINGS = ["### Added", "### Changed", "### Fixed", "### Ported"]


def _find_unreleased_index(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if line.rstrip("\n") == UNRELEASED_HEADING:
            return i
    raise ValueError(f"no {UNRELEASED_HEADING!r} heading found")


def _find_next_heading_index(lines: list[str], after: int) -> int:
    for i in range(after + 1, len(lines)):
        if lines[i].startswith("## "):
            return i
    return len(lines)


def _has_content(body: str) -> bool:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("### "):
            return True
    return False


def _is_level3_heading(line: str) -> bool:
    return line.startswith("### ") and not line.startswith("#### ")


def _drop_empty_subsections(body: str) -> str:
    """Removes '### ' subheadings (e.g. Added/Changed/Fixed) that have no
    content before the next '### ' heading or the end of the section."""
    lines = body.splitlines(keepends=True)
    heading_indices = [i for i, line in enumerate(lines) if _is_level3_heading(line)]
    if not heading_indices:
        return body

    kept = lines[: heading_indices[0]]
    for pos, start in enumerate(heading_indices):
        end = heading_indices[pos + 1] if pos + 1 < len(heading_indices) else len(lines)
        section = lines[start:end]
        if "".join(section[1:]).strip():
            kept.extend(section)
    return "".join(kept).strip("\n")


def extract_unreleased(text: str) -> str:
    lines = text.splitlines(keepends=True)
    heading_idx = _find_unreleased_index(lines)
    end_idx = _find_next_heading_index(lines, heading_idx)
    body = "".join(lines[heading_idx + 1 : end_idx]).strip("\n")
    if not _has_content(body):
        raise ValueError(f"{UNRELEASED_HEADING!r} section is empty")
    return _drop_empty_subsections(body) + "\n"


def bump_unreleased(text: str, version: str, date: str) -> str:
    lines = text.splitlines(keepends=True)
    heading_idx = _find_unreleased_index(lines)
    end_idx = _find_next_heading_index(lines, heading_idx)
    body = "".join(lines[heading_idx + 1 : end_idx]).strip("\n")
    if not _has_content(body):
        raise ValueError(f"{UNRELEASED_HEADING!r} section is empty")

    scaffold = [UNRELEASED_HEADING + "\n", "\n"]
    for subheading in SCAFFOLD_SUBHEADINGS:
        scaffold.append(subheading + "\n")
        scaffold.append("\n")

    versioned_heading = [f"## {version} - {date}\n"]

    new_lines = (
        lines[:heading_idx]
        + scaffold
        + versioned_heading
        + lines[heading_idx + 1 : end_idx]
        + lines[end_idx:]
    )
    return "".join(new_lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", type=Path, help="path to CHANGELOG.md")
    parser.add_argument("--output", type=Path, required=True, help="write release body here")
    parser.add_argument("--bump", metavar="VERSION", help="rename Unreleased to this version")
    parser.add_argument(
        "--date", help="date for --bump's version heading (default: today, UTC)"
    )
    args = parser.parse_args(argv)

    text = args.changelog.read_text(encoding="utf-8")

    try:
        body = extract_unreleased(text)
        if args.bump:
            date = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            rewritten = bump_unreleased(text, args.bump, date)
            args.changelog.write_text(rewritten, encoding="utf-8")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    args.output.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
