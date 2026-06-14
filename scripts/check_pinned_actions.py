#!/usr/bin/env python3
"""Check composite action definitions for outdated pinned-SHA external actions.

Dependabot's github-actions ecosystem only scans .github/workflows/*.yml, not
action.yml files used by composite actions, so pins inside
.github/actions/*/action.yml are not covered by Dependabot and need their own
update check.

For each `uses: <owner>/<repo>[/<path>]@<sha> # <vX.Y.Z>` reference found, this
script looks up the latest vX.Y.Z tag on the upstream repo and reports any pin
that is behind. Writes a summary to outdated.md and exits non-zero if any pins
are outdated.
"""
import re
import subprocess
import sys
from pathlib import Path

PIN_RE = re.compile(
    r"uses:\s*([\w.-]+/[\w.-]+(?:/[\w./-]+)?)@([0-9a-f]{40})\s*(?:#\s*(\S+))?"
)
TAG_RE = re.compile(r"refs/tags/(v\d+\.\d+\.\d+)(\^\{\})?$")


def latest_tag_commit(repo: str):
    """Return (tag, commit_sha) for the highest vX.Y.Z tag on repo, peeled to a commit."""
    result = subprocess.run(
        ["git", "ls-remote", "--tags", f"https://github.com/{repo}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return None

    tags = {}
    for line in result.stdout.splitlines():
        sha, ref = line.split("\t")
        m = TAG_RE.match(ref)
        if not m:
            continue
        tag, peeled = m.group(1), m.group(2)
        if peeled or tag not in tags:
            tags[tag] = sha

    if not tags:
        return None

    best = max(tags, key=lambda t: tuple(int(p) for p in t[1:].split(".")))
    return best, tags[best]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    outdated = []

    for action_file in sorted(root.glob(".github/actions/*/action.yml")):
        text = action_file.read_text()
        for m in PIN_RE.finditer(text):
            ref, sha, comment = m.group(1), m.group(2), m.group(3)
            repo = "/".join(ref.split("/")[:2])
            if repo.lower() == "mapgie/android-actions":
                continue  # self-references are updated manually, not via tags

            latest = latest_tag_commit(repo)
            if latest is None:
                continue

            latest_tag, latest_sha = latest
            if latest_sha != sha:
                outdated.append((action_file.relative_to(root), ref, sha, comment, latest_tag, latest_sha))

    if not outdated:
        print("All pinned actions in .github/actions/*/action.yml are up to date.")
        return 0

    lines = [
        "The following pinned actions in `.github/actions/*/action.yml` are behind the latest release.",
        "Dependabot does not scan `action.yml` files, so these pins need to be bumped manually "
        "(remember to update both the SHA and the version comment).",
        "",
    ]
    for rel_path, ref, sha, comment, latest_tag, latest_sha in outdated:
        print(f"{rel_path}: {ref}@{sha} ({comment}) -> {latest_tag} @ {latest_sha}")
        lines.append(
            f"- `{rel_path}`: `{ref}@{sha}` (currently `{comment or 'unknown'}`) "
            f"-> latest is `{latest_tag}` (`{latest_sha}`)"
        )

    Path("outdated.md").write_text("\n".join(lines) + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
