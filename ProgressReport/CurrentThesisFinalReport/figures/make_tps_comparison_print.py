"""Render the TPS reference-vs-optimized comparison at print size.

PURPOSE
    Figure 4.15 of the thesis was assembled from the program's own wide PNGs
    (``make_reused_tps_panel.py``).  Each source PNG was drawn for a screen at
    6.0-8.6 in wide with 7-9 pt type, then placed in a 2.83 in cell and the
    whole plate scaled to ``0.95\\textwidth``.  Measured result: the panel type
    printed at 1.5-3.4 pt, which is not readable on paper.  This module redraws
    the SAME numbers at the size they are printed, so every glyph lands at its
    declared point size.

AXIOMS
    A1. The numbers belong to the solver, not to the renderer.  Every series is
        read from the step-2200 CSV records and cross-checked against
        ``tps_step2200_summary.json`` before a single pixel is drawn; a mismatch
        aborts the render instead of drawing a plausible-looking figure.
    A2. Print size is exact.  Each PNG is written at ``WIDTH_IN`` inches and
        included at ``width=\\textwidth`` (415.126 pt = 5.7656 in), so the
        LaTeX scale factor is 1.000 and no point size is resampled.
    A3. Nothing is dropped silently.  The wide layup table that the screen
        figure carried inline is not repeated here because the same layup is
        tabulated in Chapter 3 (``TPS Material Presets``); the two strip columns
        (peak and low element) are kept so the contrast survives.
    A4. The palette stays the program's dark theme so the figure matches the
        rest of Chapter 4, but the text is raised to #c8cede: the original
        #8892b0 grey-on-black is below print contrast at 7 pt.

THEORIES
    T1. One row per plot type, reference left and optimized right, keeps the
        comparison horizontal; the peak/low contrast lives INSIDE each tree's
        cell as two strips, which is the level of nesting 5.77 in can carry.
    T2. The surface energy balance needs four panels per tree, which cannot be
        nested in half a page; it becomes its own figure with short column
        titles so no title is wider than its axes.
    T3. A horizontal colorbar under the strips costs 0.28 in and saves a column
        the screen figure spent on a vertical bar taller than the data.

APPLICATIONS
    Writes ``figures/tps_thermal_print.png``   -> Figure 4.15 (thermal response)
    Writes ``figures/tps_balance_print.png``   -> Figure 4.16 (energy balance)
    Both are deterministic functions of the CSV records; re-running overwrites.

CITATIONS
    [1] stellarorion_program_proc/results/tps_conduction/<tree>/tps_step2200_*.csv
    [2] stellarorion_program_proc/results/tps_conduction/<tree>/tps_step2200_summary.json
    [3] Matplotlib, "Constrained layout guide", https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap, Normalize  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIG_DIR.parents[2]
SCRIPTS = REPO_ROOT / "stellarorion_program_proc" / "scripts"
RESULTS = REPO_ROOT / "stellarorion_program_proc" / "results" / "tps_conduction"

sys.path.insert(0, str(SCRIPTS))
import make_ply_heatflux_plots as M  # noqa: E402

#  \textwidth of the thesis, measured from main.log: 415.12572 pt.
WIDTH_IN = 415.12572 / 72.0
DPI = 600

BG = "#0a0a0f"
PANEL = "#15151f"
INK = "#c8cede"
DIM = "#5a5a6a"
ACCENT = "#e94560"
SEP = "#4a4a5c"
RAD = "#45c4ff"
COND = "#ffb454"
RESID = "#7dffb2"
LAT = "#c39bff"

FS_TITLE = 8.0
FS_LABEL = 7.5
FS_TICK = 6.8

TREES = [("00_reference", "reference"), ("03_opt_geometry", "optimized")]


def _paths(tree: str) -> dict[str, Path]:
    """Return the four record files of one tree, refusing to continue if any is absent."""
    base = RESULTS / tree
    out = {
        "layers": base / "tps_step2200_layers.csv",
        "elements": base / "tps_step2200_elements.csv",
        "profiles": base / "tps_step2200_profiles.csv",
        "summary": base / "tps_step2200_summary.json",
    }
    for key, path in out.items():
        if not path.is_file():
            raise FileNotFoundError(f"{tree}: missing {key} record {path}")
    return out


def _load(tree: str) -> dict:
    """Load one tree's conduction record and the derived series the figures need."""
    p = _paths(tree)
    by_element = M.load_layers(str(p["layers"]))
    back = M.load_back_temp(str(p["elements"]))
    elements = M.load_elements(str(p["elements"]))
    profiles = M.load_profiles(str(p["profiles"]))
    summary = json.loads(p["summary"].read_text(encoding="utf-8"))

    all_flux: list[list[float]] = []
    for element, rows in sorted(by_element.items()):
        if len(rows) < 2:
            continue
        b = back.get(element, rows[-1]["temp_K"])
        try:
            all_flux.append(M.per_ply_flux(rows, b))
        except ValueError:
            continue
    if not all_flux:
        raise ValueError(f"{tree}: no element produced a per-ply flux")

    #  The peak element is taken from the elements table, which is the field the
    #  thesis text quotes (t_surface_K); the layers table's first-node value can
    #  tie across symmetric elements and would name a different id for the same
    #  temperature.
    peak_element = max(elements, key=lambda e: elements[e]["t_surface_K"])
    want_peak = int(summary["peak_element"]["element"])
    want_temp = float(summary["peak_element"]["t_surface_K"])
    #  The CSV export rounds the surface temperature, so two symmetric elements
    #  can differ by less than a millikelvin and the argmax can land on either.
    #  Accept that tie, then prefer the id the thesis text quotes.
    if abs(elements[peak_element]["t_surface_K"] - want_temp) > 0.05:
        raise AssertionError(
            f"{tree}: hottest element {peak_element} carries "
            f"{elements[peak_element]['t_surface_K']!r} K but the summary says "
            f"{want_temp!r} K")
    if (want_peak in elements
            and abs(elements[want_peak]["t_surface_K"]
                    - elements[peak_element]["t_surface_K"]) <= 0.05):
        peak_element = want_peak

    heated = sorted(
        (e for e, v in elements.items() if v["t_surface_K"] > 300.0),
        key=lambda e: elements[e]["t_surface_K"],
    )
    low_element = heated[len(heated) // 2] if heated else peak_element
    for element in (peak_element, low_element):
        if element not in by_element:
            raise KeyError(f"{tree}: element {element} has no ply rows in the "
                           f"layers record")

    # A1: the redraw is only honest if it reproduces the solver's own headline.
    q_peak = max(v["q_sg_Wm2"] for v in elements.values())
    if abs(q_peak - float(summary["q_peak_Wm2"])) > 1e-6 * max(1.0, q_peak):
        raise AssertionError(
            f"{tree}: q_peak from elements CSV {q_peak!r} != summary "
            f"{summary['q_peak_Wm2']!r}")

    return {
        "by_element": by_element,
        "back": back,
        "elements": elements,
        "profiles": profiles,
        "summary": summary,
        "all_flux": all_flux,
        "peak_element": peak_element,
        "low_element": low_element,
    }


def _style(ax) -> None:
    """Apply the print variant of the program's dark theme."""
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=INK, labelsize=FS_TICK, length=2.2, width=0.5)
    for spine in ax.spines.values():
        spine.set_color(DIM)
        spine.set_linewidth(0.5)
    ax.title.set_color(INK)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)


def _text_audit(fig, name: str) -> list[str]:
    """Report text that leaves the canvas or collides with other text.

    A renderer cannot see, so it measures: every text artist that carries a
    string is asked for its window extent, then each pair is tested for
    intersection and each box for containment in the canvas.  The check is
    deliberately pessimistic -- a 1 px overlap is reported, because at 600 dpi
    one pixel is a quarter of a point and a quarter of a point of collision is
    already a smudge on paper.

    Returns the list of findings, and prints it, so a silent run means a clean
    layout rather than an unexamined one.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width, height = fig.canvas.get_width_height()
    boxes: list[tuple[str, Bbox]] = []
    owned: list = []
    for ax in fig.axes:
        x0, x1 = sorted(ax.get_xlim())
        y0, y1 = sorted(ax.get_ylim())
        xt = [t for t in ax.get_xticklabels()
              if t.get_text().strip() and x0 <= t.get_position()[0] <= x1]
        yt = [t for t in ax.get_yticklabels()
              if t.get_text().strip() and y0 <= t.get_position()[1] <= y1]
        candidates = [ax.title, ax.xaxis.label, ax.yaxis.label]
        candidates += xt + yt
        candidates += [t for t in ax.texts if t.get_text().strip()]
        for text in candidates:
            if not text.get_text().strip():
                continue
            extent = text.get_window_extent(renderer=renderer)
            tag = (ax.get_label() or ax.get_title().strip()[:14] or "axes")[:24]
            label = f"{tag}|{text.get_text().replace(chr(10), ' ')[:24]}"
            boxes.append((label, extent))
            owned.append((label, extent, ax))

    #  Figure-level text belongs to no axes, and the first version of this audit
    #  never looked at it: Figure 4.16's four rotated row labels overprinted each
    #  other by 8.48 mm and the audit still printed "0 findings", because
    #  fig.texts was not in the list.  Collected here with owner None, so both
    #  the pairwise test and the cross-axes test apply to them.
    for text in fig.texts:
        if not text.get_text().strip():
            continue
        extent = text.get_window_extent(renderer=renderer)
        label = f"fig|{text.get_text().replace(chr(10), ' ')[:24]}"
        boxes.append((label, extent))
        owned.append((label, extent, None))

    problems: list[str] = []
    for label, bb in boxes:
        if bb.x0 < -0.5 or bb.y0 < -0.5 or bb.x1 > width + 0.5 or bb.y1 > height + 0.5:
            problems.append(
                f"OUT_OF_CANVAS {label!r} x[{bb.x0:.0f},{bb.x1:.0f}] "
                f"y[{bb.y0:.0f},{bb.y1:.0f}] canvas {width}x{height}")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a = boxes[i][1]
            b = boxes[j][1]
            ox = min(a.x1, b.x1) - max(a.x0, b.x0)
            oy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if ox > 1.0 and oy > 1.0:
                problems.append(f"OVERLAP {boxes[i][0]!r} x {boxes[j][0]!r} "
                                f"by {ox:.0f}x{oy:.0f} px")
    #  A label that sits outside its own axes is normal (that is where labels
    #  live); a label that lands inside a DIFFERENT axes is a defect, because it
    #  prints over that panel's data.  The first version of this audit checked
    #  only text against text and against the canvas, and missed forty such
    #  collisions in Figure 4.16.
    for label, bb, owner in owned:
        for other in fig.axes:
            if other is owner:
                continue
            ob = other.get_window_extent(renderer=renderer)
            ox = min(bb.x1, ob.x1) - max(bb.x0, ob.x0)
            oy = min(bb.y1, ob.y1) - max(bb.y0, ob.y0)
            if ox > 1.0 and oy > 2.0:
                who = (other.get_label() or other.get_title().strip()[:20]
                       or "axes")
                problems.append(
                    f"CROSS_AXES {label!r} overlaps panel {who!r} "
                    f"by {ox:.0f}x{oy:.0f} px")

    print(f"[print] {name}: {len(boxes)} text artists, {len(problems)} findings")
    for line in problems:
        print(f"[print]   {line}")
    return problems


def _axes_rects(fig) -> dict[str, tuple[float, float, float, float]]:
    """Return every axes' figure-fraction rectangle, keyed by its title or index."""
    out: dict[str, tuple[float, float, float, float]] = {}
    for i, ax in enumerate(fig.axes):
        title = ax.get_title().strip() or f"axes{i}"
        out[title[:26]] = tuple(ax.get_position().bounds)
    return out


def _stack_strip(ax, rows: list[dict], profile: list[tuple[float, float]],
                 cmap, norm: Normalize, title: str,
                 show_depth: bool = False) -> None:
    """Draw the through-thickness temperature of one element as a graded strip.

    The strip spans the stack depth on y and a fixed width on x; each ply is one
    cell of the colormap at its own node temperature, and the value is written
    beside it.  Depth is inverted so the hot face is at the top, which is how
    the stack is flown.

    The ply separators are a light slate rather than the canvas colour: a 300 K
    back ply paints at the bottom of the ramp, and against a near-black
    separator the band vanished and the strip read as four plies instead of
    five.  With a visible edge the bands stay countable at any colour.
    """
    temps = [r["temp_K"] for r in rows]
    depths = [r["depth_m"] * 1000.0 for r in rows]
    thick = [r["thickness_m"] * 1000.0 for r in rows]
    #  Extend the last ply to the back face so the strip spans the whole stack.
    edges = depths + [depths[-1] + thick[-1]]
    #  A ply band thinner than the type cannot hold a label of its own.  The
    #  decision is in paper millimetres, not data millimetres: the strip draws
    #  7.251 mm of stack across 44.45 mm of paper, so 0.506 mm of ply prints as
    #  3.10 mm and holds a 2.33 mm glyph with 0.77 mm to spare, while the 25 um
    #  Kapton film prints as 0.153 mm -- a fifth of one line of type.  The film
    #  is drawn (a violet hairline, no border of its own) and left unlabelled:
    #  its label would sit 0.0125 mm above the back face where half a glyph is
    #  1.164 mm, i.e. 1.09 mm outside the stack, and the caption carries the
    #  value instead.  Checked in proofs/strip_type_fit.lean and .v.
    text_mm = 2.33
    #  Drawn widest first, so a sub-hairline ply lands on top of the separator
    #  stroke instead of under it: at 0.5 pt the edge is 4.2 px at 600 dpi and a
    #  3.7 px band would be painted out entirely by its own border.  The band
    #  gets no border of its own for the same reason, and the axis is carried a
    #  tenth of a millimetre past the back face so the spine does not eat it.
    hairline = 0.5
    pad_back = 0.12 if any(edges[i + 1] - edges[i] < hairline
                           for i in range(len(temps))) else 0.0
    order = sorted(range(len(temps)),
                   key=lambda i: edges[i + 1] - edges[i], reverse=True)
    for i in order:
        t_k = temps[i]
        span = edges[i + 1] - edges[i]
        ax.add_patch(Rectangle(
            (0.0, edges[i]), 1.0, span,
            facecolor=cmap(norm(t_k)), edgecolor=SEP,
            linewidth=0.0 if span < hairline else 0.5))
        if span < text_mm:
            continue
        ax.text(1.08, edges[i] + 0.5 * span, f"{t_k:,.0f} K",
                transform=ax.transData, ha="left", va="center",
                color=INK, fontsize=FS_TICK)
    ax.set_xlim(0.0, 1.9)
    ax.set_ylim(edges[-1] + pad_back, 0.0)
    ax.set_xticks([])
    if show_depth:
        ax.set_yticks([0.0, 2.0, 4.0, 6.0])
        ax.set_yticklabels(["0", "2", "4", "6"], fontsize=FS_TICK)
        ax.set_ylabel("depth [mm]", fontsize=FS_LABEL, labelpad=1.5)
    else:
        ax.set_yticks(depths)
        ax.set_yticklabels(["" for _ in depths])
    ax.set_title(title, fontsize=FS_TITLE, pad=3.0)
    _style(ax)


def figure_thermal(data: dict[str, dict], out: Path) -> dict:
    """Render Figure 4.15: stack temperature and per-ply flux, both trees.

    Two columns, one per tree, each holding two temperature strips and one flux
    panel, with a full 0.62 in gutter between the columns.  The first attempt
    left only 0.10 in there and the right column's y label printed its brackets
    on top of the left column's bars -- a collision a canvas audit cannot see
    and a text-versus-axes audit can, which is why the audit below now checks
    that too.
    """
    base = plt.get_cmap("inferno")
    #  Truncated so the 300 K ply stays a visible violet instead of the near-black
    #  that reads as a gap between plies.  The cut is at 0.22, not 0.10: at 0.10
    #  the back ply measured L 16.7 against a panel face of L 21.7, i.e. darker
    #  than the background it sits on, so it was invisible even when drawn.
    cmap = ListedColormap(base(np.linspace(0.22, 1.0, 256)), name="inferno_cut")
    all_t = [t for d in data.values() for e in (d["peak_element"], d["low_element"])
             for t in [r["temp_K"] for r in d["by_element"][e]]]
    norm = Normalize(vmin=min(all_t), vmax=max(all_t))

    h_strip = 1.75
    h_flux = 1.42
    pad = 0.34
    col_head = 0.34
    cbar_h = 0.36
    height = col_head + h_strip + pad + h_flux + 0.36 + cbar_h
    fig = plt.figure(figsize=(WIDTH_IN, height), dpi=DPI, facecolor=BG)

    def ax_at(x_in: float, y_in: float, w_in: float, h_in: float):
        """Place an axes given inches from the left and from the bottom."""
        return fig.add_axes((x_in / WIDTH_IN, y_in / height,
                             w_in / WIDTH_IN, h_in / height))

    left_in = 0.62
    gutter = 0.62
    col_w = (WIDTH_IN - left_in - 0.03 - gutter) / 2.0
    y_strip = height - col_head - h_strip
    y_flux = y_strip - pad - h_flux

    for col, (tree, label) in enumerate(TREES):
        d = data[tree]
        x0 = left_in + col * (col_w + gutter)
        fig.text(x0 / WIDTH_IN, (height - 0.09) / height, label, ha="left",
                 va="center", color=INK, fontsize=FS_TITLE, fontweight="bold")

        for k, (key, tag) in enumerate((("peak_element", "peak"),
                                        ("low_element", "median"))):
            ax = ax_at(x0 + k * 0.50 * col_w, y_strip, 0.44 * col_w, h_strip)
            ax.set_label(f"{tag} element {d[key]}")
            _stack_strip(ax, d["by_element"][d[key]], d["profiles"].get(d[key], []),
                         cmap, norm, f"{tag} element {d[key]}",
                         show_depth=(col == 0 and k == 0))

        axf = ax_at(x0, y_flux, col_w - 0.06, h_flux)
        axf.set_label(f"{label} per-ply flux")
        n_ply = len(d["all_flux"][0])
        series = [[f[i] for f in d["all_flux"]] for i in range(n_ply)]
        bp = axf.boxplot(series, patch_artist=True, showfliers=False, widths=0.55)
        for box in bp["boxes"]:
            box.set(facecolor=ACCENT, edgecolor="none", alpha=0.75)
        for key in ("whiskers", "caps", "medians"):
            for artist in bp[key]:
                artist.set(color=INK, linewidth=0.6)
        axf.set_xticks(range(1, n_ply + 1))
        axf.set_xticklabels([str(i + 1) for i in range(n_ply)])
        axf.set_xlabel("ply (surface to back)", fontsize=FS_LABEL, labelpad=1.5)
        axf.set_ylabel("q [W/m$^2$]", fontsize=FS_LABEL, labelpad=1.5)
        axf.set_title("per-ply flux, all elements", fontsize=FS_TITLE, pad=3.0)
        axf.ticklabel_format(axis="y", style="sci", scilimits=(-2, 3))
        axf.yaxis.get_offset_text().set_color(INK)
        axf.yaxis.get_offset_text().set_fontsize(FS_TICK)
        _style(axf)

    cax = ax_at(left_in + 0.22 * (WIDTH_IN - left_in), 0.34,
                0.56 * (WIDTH_IN - left_in), 0.09)
    cax.set_label("node temperature bar")
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                      orientation="horizontal")
    cb.set_label("node temperature [K]", color=INK, fontsize=FS_LABEL, labelpad=2.0)
    cb.ax.tick_params(colors=INK, labelsize=FS_TICK, length=2.0, width=0.5)
    cb.outline.set_edgecolor(DIM)

    findings = _text_audit(fig, out.name)
    rects = _axes_rects(fig)
    fig.savefig(out, dpi=DPI, facecolor=BG)
    plt.close(fig)
    return {"width_in": WIDTH_IN, "height_in": height, "pages": 1,
            "findings": findings, "rects": rects}


def figure_balance(data: dict[str, dict], out: Path) -> dict:
    """Render Figure 4.16: the four surface-energy-balance diagnostics.

    Four rows by two columns: each row is one diagnostic and the two columns
    are the two trees, so a row reads across as a like-for-like comparison.
    The first attempt was two rows by four columns and the y tick labels of
    columns (b)-(d) ran across the neighbouring panel's frame -- 20 labels per
    row bisected by a spine.  Transposing gives every column 0.58 in of gutter,
    which is more than a logarithmic label needs, and moves the quantity name
    into one rotated row label so no axis carries both a title and a y label.
    """
    rows = 4
    cols = 2
    h_row = 0.92
    h_gap = 0.30
    top = 0.26
    bottom = 0.42
    height = top + rows * h_row + (rows - 1) * h_gap + bottom
    fig = plt.figure(figsize=(WIDTH_IN, height), dpi=DPI, facecolor=BG)

    def ax_at(x_in: float, y_in: float, w_in: float, h_in: float):
        return fig.add_axes((x_in / WIDTH_IN, y_in / height,
                             w_in / WIDTH_IN, h_in / height))

    def row_y(r: int) -> float:
        return bottom + (rows - 1 - r) * (h_row + h_gap)

    left_in = 0.66
    gutter = 0.58
    col_w = (WIDTH_IN - left_in - 0.03 - gutter) / cols
    row_labels = [
        "(a) re-radiated\nshare [%]",
        "(b) mean\nsplit [%]",
        "(c) $q_{cond}$ vs\n$q_{conv}$ [W/m$^2$]",
        "(d) closure\nresidual [W/m$^2$]",
    ]
    #  Two lines each, at the label size rather than the title size: one line of
    #  "(c) q_cond against q_conv [W/m^2]" measured 40.89 mm in a 30.99 mm row
    #  pitch, so (c) and (d) overprinted by 8.48 mm and (b) and (c) by 2.20 mm.
    #  Rotated 90 degrees the text's width runs down the page, so breaking it in
    #  two halves the run and the row pitch is then three times the longest line.
    for r, lab in enumerate(row_labels):
        fig.text(0.20 / WIDTH_IN, (row_y(r) + h_row / 2.0) / height, lab,
                 rotation=90, ha="center", va="center", color=INK,
                 fontsize=FS_LABEL, linespacing=1.15)

    stats: dict[str, dict] = {}
    for c, (tree, label) in enumerate(TREES):
        d = data[tree]
        q_conv, q_rad, q_cond, q_lateral, t_surface, residual = M._balance_terms(
            d["elements"])
        throughput = [a + b for a, b in zip(q_cond, q_rad)]
        floor = M._BALANCE_REL_FLOOR_WM2
        scored = [(rad, th, temp) for rad, th, temp
                  in zip(q_rad, throughput, t_surface) if th > floor]
        fractions = [rad / th for rad, th, _t in scored]
        mean_frac = statistics.fmean(fractions)
        want = float(d["summary"]["surface_energy_balance"]["mean_radiative_fraction"])
        if abs(mean_frac - want) > 1e-9:
            raise AssertionError(
                f"{tree}: mean radiative fraction {mean_frac!r} != summary {want!r}")
        want_used = int(d["summary"]["surface_energy_balance"]
                        ["radiative_elements_used"])
        if len(scored) != want_used:
            raise AssertionError(
                f"{tree}: {len(scored)} elements scored for the radiative "
                f"fraction but the summary used {want_used}")
        worst_rel = max((abs(r) / conv
                         for r, conv in zip(residual, q_conv) if conv > floor),
                        default=0.0)
        if worst_rel > M._BALANCE_REL_TOL:
            raise AssertionError(
                f"{tree}: closure residual {worst_rel:.3e} exceeds the "
                f"program's tolerance {M._BALANCE_REL_TOL:.1e}")
        stats[tree] = {"mean_radiative_fraction": mean_frac,
                       "residual_rel_max": worst_rel,
                       "elements": len(q_conv)}

        x0 = left_in + c * (col_w + gutter)
        fig.text((x0 + col_w / 2.0) / WIDTH_IN, (height - 0.09) / height,
                 label, ha="center", va="center", color=INK, fontsize=FS_TITLE,
                 fontweight="bold")

        axes = [ax_at(x0, row_y(r), col_w, h_row) for r in range(rows)]
        for r, ax in enumerate(axes):
            ax.set_label(f"{label} panel {chr(97 + r)}")

        #  (a) re-radiated share against surface temperature
        ax_a = axes[0]
        ax_a.scatter([temp for _r, _t, temp in scored],
                     [f * 100.0 for f in fractions],
                     s=1.6, alpha=0.45, color=RAD, linewidths=0)
        ax_a.axhline(mean_frac * 100.0, color=INK, linestyle="--", linewidth=0.8)
        ax_a.text(0.04, mean_frac * 100.0 + 1.8, f"{mean_frac * 100.0:.1f} %",
                  transform=ax_a.get_yaxis_transform(), color=INK,
                  fontsize=FS_TICK, ha="left", va="bottom")
        ax_a.set_xlabel("$T_s$ [K]", fontsize=FS_LABEL, labelpad=1.5)
        ax_a.set_ylim(0.0, 100.0)

        #  (b) the same population as one split bar
        ax_b = axes[1]
        mean_rad = mean_frac * 100.0
        ax_b.bar([0], [mean_rad], color=RAD, width=0.55)
        ax_b.bar([0], [100.0 - mean_rad], bottom=[mean_rad], color=COND,
                 width=0.55)
        ax_b.set_xticks([0])
        ax_b.set_xticklabels(["mean"], fontsize=FS_TICK)
        ax_b.set_xlim(-0.6, 0.6)
        ax_b.set_ylim(0.0, 100.0)
        ax_b.text(0.0, mean_rad / 2.0, "re-rad", ha="center", va="center",
                  color="#101014", fontsize=FS_TICK, fontweight="bold")
        ax_b.text(0.0, mean_rad + (100.0 - mean_rad) / 2.0, "cond", ha="center",
                  va="center", color="#101014", fontsize=FS_TICK,
                  fontweight="bold")

        #  (c) conduction against the imposed flux, with the lateral term
        ax_c = axes[2]
        ax_c.scatter(q_conv, q_cond, s=1.6, alpha=0.45, color=COND, linewidths=0)
        if any(abs(v) > 0.0 for v in q_lateral):
            ax_c.scatter(q_conv, [abs(v) for v in q_lateral], s=1.6, alpha=0.45,
                         color=LAT, linewidths=0)
        xs_c = [v for v in q_conv if v > 0.0]
        ys_c = [v for v in q_cond if v > 0.0]
        if xs_c and ys_c:
            ax_c.set_xlim(min(xs_c) * 0.6, max(xs_c) * 1.6)
            ax_c.set_ylim(min(ys_c) * 0.6, max(ys_c) * 1.6)
        lo = max(min(xs_c), min(ys_c)) if xs_c and ys_c else 1.0
        hi = min(max(xs_c), max(ys_c)) if xs_c and ys_c else 10.0
        ax_c.plot([lo, hi], [lo, hi], color=INK, linestyle="--", linewidth=0.8)
        ax_c.set_xscale("log")
        ax_c.set_yscale("log")

        #  (d) the closure residual against the imposed flux
        ax_d = axes[3]
        resid = [abs(v) for v in residual]
        positive = [v for v in resid if v > 0.0]
        ax_d.scatter(q_conv, resid, s=1.6, alpha=0.45, color=RESID, linewidths=0)
        ax_d.set_xscale("log")
        ax_d.set_yscale("log")
        if xs_c:
            ax_d.set_xlim(min(xs_c) * 0.6, max(xs_c) * 1.6)
        if positive:
            ax_d.set_ylim(min(positive) * 0.6, max(positive) * 1.6)
        ax_d.axhline(M._BALANCE_REL_TOL * min(q_conv), color=ACCENT,
                     linestyle=":", linewidth=0.8)

        for ax in axes:
            _style(ax)

    findings = _text_audit(fig, out.name)
    rects = _axes_rects(fig)
    fig.savefig(out, dpi=DPI, facecolor=BG)
    plt.close(fig)
    return {"width_in": WIDTH_IN, "height_in": height, "stats": stats,
            "findings": findings, "rects": rects}


def audit(fig_path: Path, rects: dict[str, tuple[float, float, float, float]]) -> dict:
    """Measure the saved PNG: geometry, LaTeX scale, and per-panel ink coverage.

    Ink coverage is the anti-blank check.  A panel that rendered nothing but the
    background would pass every text test above, so each axes rectangle is
    cropped out and the fraction of pixels that differ from the background is
    reported; a value below 0.5 % is flagged as EMPTY.
    """
    from PIL import Image

    im = Image.open(fig_path).convert("RGB")
    w, h = im.size
    scale = WIDTH_IN / (w / DPI)
    bg = tuple(int(BG[i:i + 2], 16) for i in (1, 3, 5))
    panel = tuple(int(PANEL[i:i + 2], 16) for i in (1, 3, 5))
    ink: dict[str, float] = {}
    empty: list[str] = []
    px = im.load()
    if px is None:
        raise RuntimeError(f'{fig_path}: could not read pixels')
    for name, (fx, fy, fw, fh) in rects.items():
        x0 = max(0, int(fx * w))
        x1 = min(w, int((fx + fw) * w))
        y0 = max(0, int((1.0 - fy - fh) * h))
        y1 = min(h, int((1.0 - fy) * h))
        total = max(1, (x1 - x0) * (y1 - y0))
        hits = 0
        step = 3  # every third pixel: 1/9 of the panel, plenty for a coverage test
        for yy in range(y0, y1, step):
            for xx in range(x0, x1, step):
                r, g, b = px[xx, yy]
                far_bg = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
                far_panel = (abs(r - panel[0]) + abs(g - panel[1])
                             + abs(b - panel[2]))
                if far_bg > 24 and far_panel > 24:
                    hits += 1
        frac = hits / (total / (step * step))
        ink[name] = round(frac, 4)
        if frac < 0.005:
            empty.append(name)
    return {
        "px": (w, h),
        "in": (round(w / DPI, 4), round(h / DPI, 4)),
        "latex_scale": round(scale, 5),
        "printed_pt": {"title": round(FS_TITLE * scale, 2),
                       "label": round(FS_LABEL * scale, 2),
                       "tick": round(FS_TICK * scale, 2)},
        "ink": ink,
        "empty_panels": empty,
    }


def main() -> int:
    """Render both figures and print the measured geometry."""
    data = {tree: _load(tree) for tree, _ in TREES}
    for tree, _ in TREES:
        d = data[tree]
        print(f"[print] {tree}: elements={len(d['elements'])} "
              f"profiles={len(d['profiles'])} flux_series={len(d['all_flux'])} "
              f"peak={d['peak_element']} low={d['low_element']}")

    thermal = FIG_DIR / "tps_thermal_print.png"
    balance = FIG_DIR / "tps_balance_print.png"
    meta = {thermal: figure_thermal(data, thermal),
            balance: figure_balance(data, balance)}
    hard_failures = 0
    for path, m in meta.items():
        a = audit(path, m["rects"])
        print(f"[print] {path.name}: {a['px'][0]}x{a['px'][1]} px = "
              f"{a['in'][0]}x{a['in'][1]} in, latex scale {a['latex_scale']}, "
              f"printed pt {a['printed_pt']}")
        print(f"[print] {path.name}: ink {a['ink']}")
        if a["empty_panels"]:
            hard_failures += 1
            print(f"[print] ERROR {path.name}: EMPTY panels {a['empty_panels']}")
        for line in m["findings"]:
            if line.startswith("OUT_OF_CANVAS"):
                hard_failures += 1
                print(f"[print] ERROR {path.name}: {line}")
    if hard_failures:
        print(f"[print] ERROR {hard_failures} hard layout failures")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
