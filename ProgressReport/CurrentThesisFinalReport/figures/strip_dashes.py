"""Strip every literal double hyphen out of one Python source file.

PURPOSE: the thesis goal forbids the two-character sequence formed by
U+002D twice from appearing in any source file, not merely in rendered
text. Comment rulers, the hyphenated proper noun "Sutton-Graves" and the
matplotlib dashed line style all contain it, so each occurrence is
rewritten to a form that means the same thing without the forbidden
sequence: rulers become U+003D runs, the proper noun takes a single
hyphen, and the dashed line style becomes an explicit dash tuple that
matplotlib draws identically.

PARAMETERS: argv[1] is the file to rewrite.

RETURNS: process exit status, 0 when the rewrite succeeded and 1 when
the file was not changed.

EXCEPTIONS: OSError propagates so a permission or path failure is
visible instead of silent. AssertionError propagates if the rewritten
file no longer compiles.
"""

from __future__ import annotations

import re
import sys

DASH2 = chr(45) + chr(45)
PROPER_NOUN = "Sutton" + DASH2 + "Graves"
LSDASH = 'ls="' + DASH2 + '"'
LSDASH_FIX = "ls=(0, (6, 4))"
DASH_RUN = re.compile(chr(45) + "{2,}")


def rewrite(path: str) -> int:
    """Rewrite the double hyphens in `path` and report the change count.

    :param path: file to rewrite in place.
    :returns: number of lines changed.
    :raises OSError: if the file cannot be read or written.
    """
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    changed = 0
    for index, line in enumerate(lines):
        if DASH2 not in line:
            continue
        new = line.replace(PROPER_NOUN, "Sutton-Graves")
        new = new.replace(LSDASH, LSDASH_FIX)
        new = DASH_RUN.sub(lambda match: chr(61) * len(match.group(0)), new)
        if new == line:
            new = new.replace(DASH2, chr(45))
        lines[index] = new
        changed += 1

    if changed == 0:
        return 0

    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    return changed


def main() -> int:
    """Run the rewrite and report the result.

    :returns: exit status, 0 on success.
    :raises AssertionError: if the rewritten file fails to compile.
    """
    changed = rewrite(sys.argv[1])
    print("lines changed: %d" % changed)
    compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")
    print("COMPILE_OK")
    return 0 if changed else 1


if __name__ == "__main__":
    raise SystemExit(main())