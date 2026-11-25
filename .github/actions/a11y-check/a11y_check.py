#!/usr/bin/env python3
"""
a11y_check.py — Accessibility role checker for Compose apps.

Scans Compose source files for .clickable / .combinedClickable modifier chains
that lack a companion .semantics { role = Role.* } declaration.

Every custom clickable element must declare an explicit role so TalkBack,
Switch Access, and keyboard navigation can discover and activate it.
See the calling app's LESSONS.md (Android / Compose) for the correct pattern.

This is the one copy shared by every app that uses android-build-release.yml.
It runs from the app's repository root, via the a11y-check composite action.
To run it locally, from the app's root with android-Actions cloned beside it:

    python3 ../android-Actions/.github/actions/a11y-check/a11y_check.py

Usage:
    python3 a11y_check.py                 # check all source files
    python3 a11y_check.py --fails-only    # same (alias, kept for parity)
    python3 a11y_check.py path/to/file.kt # check a single file

Exit: 0 = no violations | 1 = one or more violations found
"""

import os
import re
import sys
from pathlib import Path

SEARCH_ROOTS = ["app/src/main/java"]

# Lines either side of a .clickable call to search for a role declaration.
# Modifier chains are typically 2-10 lines; 15 gives comfortable headroom.
ROLE_WINDOW = 15

# Matches genuine method calls, not mentions inside comments or strings.
CLICKABLE_RE = re.compile(r"\.(clickable|combinedClickable)\s*[{(]")
ROLE_RE      = re.compile(r"\brole\s*=\s*Role\.")

# Jetpack Glance widgets use androidx.glance.action.clickable(Action), an
# unrelated API to Compose's Modifier.clickable{}/combinedClickable{}. Glance
# has no Modifier.semantics{role=Role.*} equivalent; its accessible labels
# come from the Text/Button/CheckBox content itself. Files that import
# Glance's clickable are exempt from this check.
GLANCE_CLICKABLE_IMPORT_RE = re.compile(r"^import androidx\.glance\.action\.clickable\b")


def find_kt_files(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        for dirpath, _, names in os.walk(root):
            for name in names:
                if name.endswith(".kt"):
                    files.append(Path(dirpath) / name)
    return sorted(files)


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return (1-based line number, stripped text) for each violation."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    if any(GLANCE_CLICKABLE_IMPORT_RE.match(line.strip()) for line in lines):
        return []

    violations: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith("//") or stripped.startswith("*"):
            continue

        if not CLICKABLE_RE.search(line):
            continue

        # Check surrounding window for a role declaration
        lo = max(0, i - ROLE_WINDOW)
        hi = min(len(lines), i + ROLE_WINDOW + 1)
        window = "\n".join(lines[lo:hi])

        if not ROLE_RE.search(window):
            violations.append((i + 1, stripped))

    return violations


def main() -> int:
    args      = sys.argv[1:]
    file_args = [a for a in args if not a.startswith("--")]

    files = [Path(f) for f in file_args] if file_args else find_kt_files(SEARCH_ROOTS)

    checked    = 0
    violations = 0

    for path in files:
        hits = check_file(path)
        checked += 1
        if hits:
            violations += len(hits)
            print(f"\n{path}")
            for lineno, text in hits:
                print(f"  line {lineno:4d}:  {text}")

    print(f"\n{'═'*70}")
    print(f"  {checked} file(s) checked")
    if violations:
        print(f"  {violations} violation(s)  ✗")
        print(f"\n  Each .clickable / .combinedClickable must carry")
        print(f"  .semantics {{ role = Role.<Type> }} in the same modifier chain.")
        print(f"  See LESSONS.md (Android / Compose) for the correct pattern.")
    else:
        print(f"  All clean  ✓")
    print(f"{'═'*70}")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
