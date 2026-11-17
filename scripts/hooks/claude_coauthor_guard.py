#!/usr/bin/env python3
"""Pre-push guard: reject pushes containing commits with invalid (Claude) co-authors."""
import re
import subprocess
import sys

PATTERNS = [
    re.compile(r"Co-?[Aa]uthored-?[Bb]y:.*claude", re.IGNORECASE),
    re.compile(r"Co-?[Aa]uthored-?[Bb]y:.*anthropic\.com", re.IGNORECASE),
]


def commits_for(refs_text: str):
    seen = set()
    out = []
    for line in refs_text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        _local_ref, local_oid, _remote_ref, remote_oid = parts[:4]
        if len(local_oid) < 40 or set(local_oid) == {"0"}:
            continue  # deletion
        if remote_oid and remote_oid != "0" * 40 and len(remote_oid) == 40:
            rng = f"{remote_oid}..{local_oid}"
        else:
            rng = local_oid
        try:
            r = subprocess.run(
                ["git", "rev-list", rng],
                capture_output=True, text=True, check=False,
            )
        except (OSError, subprocess.SubprocessError) as e:
            print(f"guard: rev-list failed for {rng}: {e}", file=sys.stderr)
            continue
        for c in r.stdout.split():
            if c not in seen:
                seen.add(c)
                out.append(c)
    return out


def main() -> int:
    refs = sys.stdin.read()
    bad = []
    for c in commits_for(refs):
        try:
            msg = subprocess.check_output(
                ["git", "show", "-s", "--format=%B", c], text=True,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError) as e:
            print(f"guard: show failed for {c}: {e}", file=sys.stderr)
            continue
        if any(p.search(msg) for p in PATTERNS):
            bad.append(c)
    if bad:
        sys.stderr.write("pre-push: commits with invalid (Claude) co-author detected:\n")
        for c in bad:
            sys.stderr.write(f"  {c}\n")
        sys.stderr.write("Strip the co-author (amend/rewrite) and retry.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())