#!/usr/bin/env python3
# Copyright (c) 2026 Wahyu Suryo Samudro, Institut Teknologi Bandung.
# SPDX-License-Identifier: MIT
"""Resolve the deck's typefaces against the faces this machine actually has.

WHY THIS EXISTS
    The owner asked for two specific faces: "Abadi" for the titles and
    "Abadi MT" for everything else. A .pptx stores a font NAME, never the
    glyphs, so a name the machine cannot resolve is silently replaced by
    whatever the renderer picks. On this machine the family "Abadi MT" is
    NOT installed: Microsoft Office ships "Abadi MT Condensed Light" and
    "Abadi MT Condensed Extra Bold", while the Office cloud font cache
    holds the family "Abadi" with its Regular, Bold, Italic and Bold
    Italic styles. Writing "Abadi MT" would therefore produce a deck that
    looks like the owner asked for on a machine that has the face, and
    like something else here. This module turns that silent substitution
    into a measured choice: it indexes the families this machine really
    has and picks the first face of the preference list that is present.

THEORIES
    1. A font family is available when a font FILE on this machine carries
       that exact family name. The name table is the only authority that
       the renderer and the measurement tool agree on.
    2. The preference order encodes the owner's intent from most to least
       faithful, so the resolved face is always the closest one that can
       actually be drawn.
    3. A deck that cannot be drawn is a defect, not a style, so the
       resolver never returns an empty name: it always ends on a face
       that exists.

APPLICATIONS
    - make_pptx.py resolves the title face and the text face once, at
      import time, and prints the result so that a substitution is
      visible in the build log instead of being invisible on the slide.

CITATIONS
    - Pillow 13.0.0 -- https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
    - ECMA-376 Part 1, DrawingML -- a run carries a typeface NAME, never the glyphs
    - Microsoft Office DFonts and the Office cloud font cache -- the source of the Abadi faces
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from PIL import ImageFont

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

#: The macOS font directories that every user of the machine shares.
#: WHY THEY ARE WRITTEN OUT: macOS publishes these two locations as the
#: system font directories and offers no discovery API for them in pure
#: Python. The per-user directory and the vendor directories are NOT
#: written out: they are found by globbing, so no vendor identifier and
#: no home directory is baked into the source.
SYSTEM_FONT_DIRECTORIES = (Path("/System/Library/Fonts"), Path("/Library/Fonts"))

#: Suffixes that count as an installable font file.
FONT_FILE_SUFFIXES = frozenset({".ttf", ".otf", ".ttc"})

#: The face the deck falls back to when no preferred face can be found.
LAST_RESORT_FONT = "Helvetica"

#: The style name of the upright cut of a family.
REGULAR_STYLE = "Regular"
#: The size the probe font is loaded at. It does not affect the family
#: name, it only needs to be large enough for the rasteriser to accept.
PROBE_FONT_SIZE = 20


def _font_directories() -> list[Path]:
    """Return every directory that may hold a font file on this machine.

    Returns:
        The system font directories, the per-user font directory, the
        DFonts directory of every installed application bundle, and the
        cloud font cache of every Office installation.
    """
    directories = [Path.home() / "Library/Fonts", *SYSTEM_FONT_DIRECTORIES]

    for root in (Path("/Applications"), Path.home() / "Applications"):
        if not root.is_dir():
            continue
        for bundle in root.glob("*.app"):
            candidate = bundle / "Contents" / "Resources" / "DFonts"
            if candidate.is_dir():
                directories.append(candidate)

    group_containers = Path.home() / "Library" / "Group Containers"
    if group_containers.is_dir():
        for office in group_containers.glob("*.Office"):
            directories.extend(
                candidate for candidate in office.glob("FontCache/*/CloudFonts/*") if candidate.is_dir()
            )

    return directories


def _name_of(path: Path) -> tuple[str | None, str | None] | None:
    """Return the family and style names of one font file.

    Args:
        path: The font file to inspect.

    Returns:
        The family name and the style name, or None when the file cannot be
        read as a font.
    """
    try:
        font = ImageFont.truetype(str(path), PROBE_FONT_SIZE)
    except OSError:
        return None
    return font.getname()


@cache
def _font_files_by_family() -> Mapping[str, Path]:
    """Return the font file of every family this machine can actually draw.

    WHY A REGULAR FILE IS PREFERRED: one family may ship several styles, and
    the Regular one is the face a measurement of ordinary body text has to
    use. A family that has no Regular file falls back to the first file
    that was found for it.

    Returns:
        A read-only mapping from family name to the file that carries it.
    """
    regular: dict[str, Path] = {}
    other: dict[str, Path] = {}
    for directory in _font_directories():
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.suffix.lower() not in FONT_FILE_SUFFIXES:
                continue
            names = _name_of(path)
            if names is None:
                continue
            family, style = names
            if family is None or style is None:
                continue
            if family in regular:
                continue
            if style == REGULAR_STYLE:
                regular[family] = path
            else:
                _ = other.setdefault(family, path)
    return MappingProxyType({**other, **regular})


@cache
def available_font_families() -> frozenset[str]:
    """Return every font family this machine can actually draw.

    Returns:
        The set of family names found in the font files of this machine.
    """
    return frozenset(_font_files_by_family())


def font_file_for(family: str) -> Path | None:
    """Return the font file that carries a family name.

    WHY THE FILE MATTERS: a glass pill that hugs its text has to know how
    wide that text is, and the only width that matches what the renderer
    will draw is the one the font file the deck names produces.

    Args:
        family: The family name to look for.

    Returns:
        The file that carries the family, or None when the family is absent.
    """
    return _font_files_by_family().get(family)


def resolve_font(preferred: Sequence[str], fallbacks: Sequence[str] = ()) -> str:
    """Return the first face of the preference list that this machine has.

    Args:
        preferred: The faces to try, most faithful first.
        fallbacks: The faces to try when none of the preferred ones is
            installed.

    Returns:
        The name of an installed face. When neither list yields a face
        that exists, the last resort face is returned.
    """
    families = available_font_families()
    for name in (*preferred, *fallbacks):
        if name in families:
            return name
    return LAST_RESORT_FONT


def font_is_installed(name: str) -> bool:
    """Report whether a font family is installed on this machine.

    Args:
        name: The family name to look for.

    Returns:
        True when a font file on this machine carries that family name.
    """
    return name in available_font_families()


if __name__ == "__main__":
    import sys

    for family in sorted(available_font_families()):
        _ = sys.stdout.write(f"{family}\n")
