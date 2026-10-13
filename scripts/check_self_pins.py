#!/usr/bin/env python3
"""Check this repo's references to itself for pins that run outdated code.

Files here reference each other by SHA (release.yml calls
android-build-release.yml, which uses the setup-gradle-env action).
Dependabot is told to ignore these self-references, because it would bump
them on every commit to main, whether or not the referenced file changed, and
every such bump starts a new round of bump PRs in each caller.

This script flags a self-pin only when the code it runs differs from main:
the referenced file (or action directory) at the pinned SHA is compared with
HEAD, ignoring the SHAs of nested self-references, which are checked by
following them to the code they point at. A stale pin should be moved to the
last commit that changed the referenced path, which this script prints.

Writes a summary to self_pins.md and exits non-zero if any pin is stale.
Needs full history (actions/checkout with fetch-depth: 0).
"""
import re
import subprocess
import sys
from pathlib import Path

SELF = "mapgie/android-actions"
SELF_PIN_RE = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)/([\w./-]+)@([0-9a-f]{40})")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def files_at(sha: str, path: str) -> dict:
    """Return {file path: content} for path (a file or directory) at sha."""
    listing = git("ls-tree", "-r", "--name-only", sha, "--", path)
    if listing.returncode != 0:
        return {}
    return {
        name: git("show", f"{sha}:{name}").stdout
        for name in listing.stdout.splitlines()
    }


def self_pins(text: str):
    """Yield (path, sha) for each reference to this repo in text."""
    for m in SELF_PIN_RE.finditer(text):
        if m.group(1).lower() == SELF:
            yield m.group(2), m.group(3)


def blank_self_shas(text: str) -> str:
    return SELF_PIN_RE.sub(
        lambda m: m.group(0).replace(m.group(3), "<sha>")
        if m.group(1).lower() == SELF
        else m.group(0),
        text,
    )


def runs_current_code(path: str, sha: str, seen=None) -> bool:
    """True if path at sha runs the same code as path at HEAD."""
    seen = set() if seen is None else seen
    if (path, sha) in seen:
        return True
    seen.add((path, sha))

    old, new = files_at(sha, path), files_at("HEAD", path)
    if not old or old.keys() != new.keys():
        return False
    for name in old:
        if blank_self_shas(old[name]) != blank_self_shas(new[name]):
            return False
        for nested_path, nested_sha in self_pins(old[name]):
            if not runs_current_code(nested_path, nested_sha, seen):
                return False
    return True


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    sources = sorted(root.glob(".github/workflows/*.yml")) + sorted(
        root.glob(".github/actions/*/action.yml")
    )

    stale = []
    for source in sources:
        rel = source.relative_to(root)
        for path, sha in self_pins(source.read_text()):
            if not runs_current_code(path, sha):
                target = git("log", "-1", "--format=%H", "HEAD", "--", path).stdout.strip()
                stale.append((rel, path, sha, target))

    if not stale:
        print("All self-references run the same code as main.")
        return 0

    lines = [
        "These references to `mapgie/android-Actions` run code that differs from `main`.",
        "Move each pin to the commit shown: the last commit that changed the referenced path.",
        "",
    ]
    for rel, path, sha, target in stale:
        print(f"{rel}: {path}@{sha} -> {target}")
        lines.append(f"- `{rel}`: `{path}@{sha[:7]}` -> `{target}`")

    Path("self_pins.md").write_text("\n".join(lines) + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
