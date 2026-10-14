"""Shared pixel-audit helpers for the two flowchart PNGs.

AXIOMS
  A1. Ground truth is the raster: every reported number comes from a pixel
      probe (numpy/PIL), never from an image viewer.
  A2. The generator source (make_methodology_figures.py) fixes data->pixel
      geometry; the affine fit is validated against >=3 independent raster
      features before any measurement is trusted.
  A3. Colour classes are separated by exact/near-exact RGB matching against
      the palette constants declared in the generator.
THEORIES
  T1. Distance transforms give exact min-gap between two pixel classes even
      when shapes are concave (arrowheads, rounded boxes).
APPLICATIONS
  A1. probe_common is imported by audit_solver_coupling.py and
      audit_result_extraction.py.
CITATIONS
  scipy.ndimage.distance_transform_edt - https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.distance_transform_edt.html
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

# Palette from make_methodology_figures.py (lines 78-86).
INK = (33, 33, 33)          # #212121
SLATE = (55, 71, 79)        # #37474F arrow colour
ORANGE = (230, 81, 0)       # #E65100 feedback colour
EDGE_COLORS = [(47, 125, 51), (22, 101, 192), (230, 82, 1), (75, 21, 140), (192, 193, 194)]
FILL_COLORS = [(63, 135, 66), (40, 113, 197), (232, 95, 20), (88, 39, 149), (229, 243, 253)]


def load(path: str) -> np.ndarray:
    """Load an RGBA PNG as an int RGB array.

    :param path: filesystem path to the PNG.
    :returns: HxWx3 int array.
    :raises OSError: if the file cannot be opened.
    """
    return np.array(Image.open(path).convert("RGB")).astype(int)


def near(a: np.ndarray, rgb, tol: int) -> np.ndarray:
    """Boolean mask of pixels within Chebyshev tolerance of rgb.

    :param a: HxWx3 int array.
    :param rgb: (r,g,b) target.
    :param tol: max per-channel absolute difference.
    :returns: HxW bool mask.
    """
    return np.abs(a - np.array(rgb)).max(axis=2) <= tol


def text_mask(a: np.ndarray) -> np.ndarray:
    """Mask of INK (#212121) text cores, excluding graphics.

    Slack 30: SLATE arrow cores are 46 away per-channel and MUST be
    excluded (slack 55 wrongly pulled arrow shafts into text clusters);
    DejaVu stems at ~40px em have solid INK cores well inside 30.
    Anti-aliased text edges beyond 30 are dropped, which only shrinks
    measured ink by <=2px and never merges separate labels.
    :param a: HxWx3 int array.
    :returns: HxW bool mask.
    """
    return np.abs(a - np.array(INK)).max(axis=2) <= 30


def color_mask(a: np.ndarray, colors, tol: int = 3) -> np.ndarray:
    """Mask of pixels matching any colour in colours within tol.

    :param a: HxWx3 int array.
    :param colors: iterable of (r,g,b).
    :param tol: per-channel tolerance.
    :returns: HxW bool mask.
    """
    out = np.zeros(a.shape[:2], bool)
    for c in colors:
        out |= near(a, c, tol)
    return out


def components(mask: np.ndarray, min_area: int = 1):
    """Labelled connected components with bboxes, largest first.

    :param mask: HxW bool.
    :param min_area: drop components smaller than this many pixels.
    :returns: list of (x0, y0, x1, y1, area) inclusive coords.
    """
    lab, _n = ndimage.label(mask)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        area = int((lab[sl] == i).sum())
        if area < min_area:
            continue
        ys, xs = sl
        out.append((int(xs.start), int(ys.start), int(xs.stop) - 1, int(ys.stop) - 1, area))
    out.sort(key=lambda t: -t[4])
    return out


def cluster_x(comps, gap: int):
    """Group components into word/label clusters by x-gaps.

    :param comps: component tuples (x0,y0,x1,y1,area).
    :param gap: max x-gap (px) still considered the same cluster.
    :returns: list of (x0,y0,x1,y1,n) merged bboxes ordered by x.
    """
    if not comps:
        return []
    cs = sorted(comps, key=lambda c: c[0])
    groups = [[cs[0]]]
    for c in cs[1:]:
        if c[0] - groups[-1][-1][2] <= gap:
            groups[-1].append(c)
        else:
            groups.append([c])
    out = []
    for g in groups:
        out.append((min(c[0] for c in g), min(c[1] for c in g),
                    max(c[2] for c in g), max(c[3] for c in g), len(g)))
    return out


def min_gap(px_pts: np.ndarray, other_mask: np.ndarray) -> float:
    """Minimum euclidean distance from point set to a boolean mask.

    :param px_pts: (N,2) int array of (x, y) points.
    :param other_mask: HxW bool mask.
    :returns: min distance in px; -1.0 if other_mask is empty.
    """
    if not other_mask.any():
        return -1.0
    d = ndimage.distance_transform_edt(~other_mask)
    vals = d[px_pts[:, 1], px_pts[:, 0]]
    return float(vals.min())


def pts_of(mask: np.ndarray) -> np.ndarray:
    """(N,2) array of (x,y) for True pixels.

    :param mask: HxW bool.
    :returns: (N,2) int array.
    """
    ys, xs = np.nonzero(mask)
    return np.stack([xs, ys], axis=1)


def ocr_multi(crop_path: str, psms=(7, 13, 6), scale: int = 3) -> dict:
    """OCR one crop under several psm modes with binarisation.

    :param crop_path: path to a saved PNG crop (white background).
    :param psms: tesseract page segmentation modes to try.
    :param scale: integer upscale factor applied before OCR.
    :returns: dict mapping "psmN" to recognised text (or an error tag).
    """
    out = {}
    for psm in psms:
        out[f"psm{psm}"] = ocr(crop_path, psm=psm, scale=scale, binarize=True)
    return out


def ocr(crop_path: str, psm: int = 7, scale: int = 2,
        binarize: bool = False) -> str:
    """OCR a crop with tesseract, up-scaled for accuracy.

    :param crop_path: path to a saved PNG crop (white background).
    :param psm: tesseract page segmentation mode.
    :param scale: integer upscale factor applied before OCR.
    :returns: stripped recognised text, or "<OCR_UNAVAILABLE: ...>".
    """
    if shutil.which("tesseract") is None:
        return "<OCR_UNAVAILABLE: tesseract not on PATH>"
    img = Image.open(crop_path).convert("L")
    img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    if binarize:
        # Threshold at 200: INK cores are <=63 gray, background is 255, so
        # this removes anti-alias haze that makes tesseract drop edge glyphs.
        img = img.point(lambda v: 255 if v > 200 else 0)
    up = str(Path(crop_path).with_suffix(".ocr.png"))
    img.save(up)
    try:
        r = subprocess.run(["tesseract", up, "stdout", "--psm", str(psm)],
                           capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"<OCR_FAILED: {exc}>"
    if r.returncode != 0:
        return f"<OCR_FAILED rc={r.returncode}: {r.stderr.strip()[:200]}>"
    return " ".join(r.stdout.split())


def save_crop(a: np.ndarray, bbox, out: str, pad: int = 8) -> str:
    """Save a padded crop of bbox; returns the path.

    :param a: HxWx3 int array.
    :param bbox: (x0,y0,x1,y1) inclusive.
    :param out: destination png path.
    :param pad: padding px added on every side (clipped to image).
    :returns: the output path.
    """
    x0, y0, x1, y1 = bbox
    H, W = a.shape[:2]
    sx0, sy0 = max(0, x0 - pad), max(0, y0 - pad)
    sx1, sy1 = min(W - 1, x1 + pad), min(H - 1, y1 + pad)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a[sy0:sy1 + 1, sx0:sx1 + 1].astype("uint8")).save(out)
    return out


def grouped_runs(idx: np.ndarray):
    """Split sorted indices into contiguous runs.

    :param idx: 1-D sorted int array.
    :returns: list of (start, end) inclusive.
    """
    if len(idx) == 0:
        return []
    runs = []
    s = p = int(idx[0])
    for v in idx[1:]:
        v = int(v)
        if v != p + 1:
            runs.append((s, p))
            s = v
        p = v
    runs.append((s, p))
    return runs
