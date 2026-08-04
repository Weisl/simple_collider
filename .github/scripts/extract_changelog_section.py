#!/usr/bin/env python3
"""Extract a single version's section from a CHANGELOG.md for use as GitHub release notes.

Looks for a Markdown heading line starting with "## " that contains the given
version (e.g. "v1.2.0"), followed by a non-digit/non-dot character or end of
line (so "v1.2.0" doesn't accidentally match "v1.2.0-rc1" or "v1.2.01"). Prints
everything between that heading and the next "## " heading (or EOF), with
leading/trailing blank lines stripped.
"""

import argparse
import re
import sys


def extract_section(changelog_text: str, version: str) -> str | None:
    version_re = re.compile(re.escape(version) + r"([^0-9.]|$)")
    lines = changelog_text.splitlines()

    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        if start is None:
            if version_re.search(line):
                start = i + 1
            continue
        end = i
        break

    if start is None:
        return None

    section_lines = lines[start:end]
    while section_lines and not section_lines[0].strip():
        section_lines.pop(0)
    while section_lines and not section_lines[-1].strip():
        section_lines.pop()
    return "\n".join(section_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changelog", required=True, help="Path to CHANGELOG.md")
    parser.add_argument("--version", required=True, help="Version to extract, e.g. v1.2.0 or 1.2.0")
    parser.add_argument("--product-name", required=True, help="Display name used in the error message, e.g. 'Simple Collider'")
    parser.add_argument("--output", required=True, help="Path to write the extracted section to")
    args = parser.parse_args()

    version = args.version[1:] if args.version.startswith("v") else args.version

    with open(args.changelog, "r", encoding="utf-8") as f:
        text = f.read()

    section = extract_section(text, version)
    if not section:
        print(
            f"::error::No CHANGELOG.md section found for version {version} "
            f"(tag v{version}). Add a '## {args.product_name} v{version}' section before tagging.",
            file=sys.stderr,
        )
        return 1

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(section + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
