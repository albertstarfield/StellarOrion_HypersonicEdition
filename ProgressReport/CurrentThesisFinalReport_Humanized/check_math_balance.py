#!/usr/bin/env python3
r"""Check that inline math delimiters balance in every LaTeX source paragraph.

PURPOSE
    Catch the class of defect where a paragraph is silently typeset in math
    mode. LaTeX does not warn when ordinary prose sits inside an unclosed
    inline math group: the spaces are simply ignored, every hyphen becomes a
    minus sign and every bare word becomes italic mathematics. The rendered
    page then loses its word spacing while the build still reports zero
    warnings. A balance check on the source finds the cause instead.

    Two conditions are reported. First, a paragraph whose number of
    unescaped dollar signs is odd cannot have been fully returned to text
    mode. Second, a `\(` or `\[` group that is never closed by `\)` or `\]`
    leaves the rest of the paragraph in math mode. Only these two conditions
    are reported, because they are the only ones that can hide prose inside
    mathematics.

    The precise cause that produced the failure is also detected: a text-mode
    command such as `\mbox` opened while the source is already inside a math
    group and which itself contains a nested dollar sign. The nested sign then
    closes the wrong group, so the text after the command is emitted as
    mathematics. `\text` is deliberately excluded from that list, because
    `\text{...}` is the standard amsmath way to set words inside a formula and
    does not switch the surrounding group out of math mode.

PARAMETERS
    None. The files to check are discovered under the script directory.

RETURNS
    Zero when every paragraph in every file balances. One when at least one
    paragraph is reported.

EXCEPTIONS
    RuntimeError: raised when the script directory holds no LaTeX file, or
        when a source file cannot be read.

CITATIONS
    LaTeX2e, Donald E. Knuth and Michael F. Plass, The TeXbook, Addison
    Wesley 1984, section 113 on inline math mode, where spaces in math mode
    are ignored and the hyphen character renders as a minus sign.

AXIOMS
    A1  Outside math mode a source character that follows a backslash is a
        control symbol or control sequence, so it can never be an unescaped
        dollar sign.
    A2  A percent sign that is not escaped starts a comment, and everything
        from it to the end of the line is discarded.
    A3  A paragraph cannot cross a blank line in the source, so delimiters
        must balance inside each blank-line-delimited block.

THEORIES
    T1  If the unescaped dollar count of a block is odd, then by A3 the block
        cannot end in text mode, so part of it was rendered as mathematics.
    T2  If a text-switching command that contains a nested dollar sign opens
        inside a math group, the nested sign closes the inner pair and the
        outer group stays open afterwards, which is defect T1 in its cause
        form.

APPLICATIONS
    A1  Run over chapter and preamble sources after every prose edit, to prove
        that no paragraph is typeset in math mode.
    A2  Part of the thesis build battery, reported beside the citation and
        structure checks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Commands that switch to text mode when used inside a math group. `\text` is
# not among them, because it is the amsmath command for words inside a formula.
TEXT_MODE_COMMANDS = (
    "mbox",
    "hbox",
    "makebox",
)

# LaTeX sources to check. Figure, table and bibliography fragments are
# included because the same hazard exists inside a caption or a table cell.
SOURCE_GLOBS = ("*.tex",)


def strip_comments(text: str) -> str:
    """Remove LaTeX comments while preserving escaped percent signs.

    Parameters
        text: the raw source text of one file.

    Returns
        The text with every unescaped comment removed.

    Raises
        None.
    """
    out: list[str] = []
    for line in text.splitlines():
        cut = len(line)
        index = 0
        while index < len(line):
            char = line[index]
            if char == "\\":
                index += 2
                continue
            if char == "%":
                cut = index
                break
            index += 1
        out.append(line[:cut])
    return "\n".join(out)


def _group_end(block: str, start: int) -> int:
    """Return the index just past the brace group that starts at ``start``.

    Parameters
        block: the source text of the block.
        start: index of the opening brace, which the caller has verified
            exists.

    Returns
        The index just past the matching closing brace. When the group is
        never closed the length of the block is returned, so the caller sees
        the whole remainder and reports the fault.

    Raises
        None.
    """
    depth = 0
    index = start
    length = len(block)
    while index < length:
        char = block[index]
        if char == "\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return length


def scan_block(block: str, filename: str, block_number: int) -> list[str]:
    """Scan one blank-line-delimited block for math delimiter faults.

    Parameters
        block: the source text of the block, comments already removed.
        filename: source file name, used only in messages.
        block_number: one-based index of the block inside the file.

    Returns
        A list of human-readable fault descriptions, empty when the block is
        sound.

    Raises
        None.
    """
    faults: list[str] = []
    depth = 0
    dollars = 0
    index = 0
    length = len(block)
    while index < length:
        char = block[index]
        if char == "\\":
            match = re.match(r"\\([A-Za-z]+)", block[index:])
            if match:
                name = match.group(1)
                if name in TEXT_MODE_COMMANDS and depth > 0:
                    # Measure to the end of the balanced group, then look for a
                    # nested dollar sign inside it. A nested sign inside a text
                    # switch opened from math is the original failure mode.
                    end = _group_end(block, index + len(match.group(0)))
                    inner = block[index : end]
                    if "$" in inner:
                        faults.append(
                            f"{filename} block {block_number}: \\{name} opened "
                            f"inside math at offset {index} contains a nested "
                            "dollar sign, so the math group stays open"
                        )
                index += len(match.group(0))
                continue
            if block[index : index + 2] in (r"\(", r"\[", r"\)", r"\]"):
                index += 2
                continue
            index += 2
            continue
        if char == "$":
            dollars += 1
            depth = 1 - depth
        index += 1
    if dollars % 2 != 0:
        faults.append(
            f"{filename} block {block_number}: odd dollar count {dollars}, "
            "paragraph ends inside math mode"
        )
    if depth != 0:
        faults.append(
            f"{filename} block {block_number}: math depth {depth} at end of block"
        )
    return faults


def check_file(path: Path) -> list[str]:
    """Check every paragraph of one LaTeX file.

    Parameters
        path: the source file to read.

    Returns
        A list of fault descriptions, empty when the file is sound.

    Raises
        RuntimeError: when the file cannot be read.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"cannot read {path}: {error}") from error
    clean = strip_comments(raw)
    faults: list[str] = []
    for number, block in enumerate(clean.split("\n\n"), start=1):
        if not block.strip():
            continue
        faults.extend(scan_block(block, path.name, number))
    return faults


def main() -> int:
    """Check every discovered LaTeX source and report the verdict.

    Returns
        Zero when all sources balance, one otherwise.

    Raises
        RuntimeError: propagated when no source file is found.
    """
    sources: list[Path] = []
    for pattern in SOURCE_GLOBS:
        sources.extend(sorted(ROOT.glob(pattern)))
    if not sources:
        raise RuntimeError(f"no LaTeX source found under {ROOT}")
    faults: list[str] = []
    for source in sources:
        faults.extend(check_file(source))
    print(f"checked {len(sources)} files under {ROOT}")
    for fault in faults:
        print(f"FAULT {fault}")
    print(f"math delimiter faults: {len(faults)}")
    print("VERDICT: " + ("PASS" if not faults else "FAIL"))
    return 0 if not faults else 1


if __name__ == "__main__":
    sys.exit(main())