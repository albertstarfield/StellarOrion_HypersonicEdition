#!/usr/bin/env python3
"""Add the two missing checks and the fourth-power frame they argue about.

The register ends with four issues but only two checks; issues 3 and 4 were
elaborated and never judged on their own frame.  This script:

  * clones the check skeleton (frame 46, "DOES THAT SOLVE ISSUE 1?") twice,
    inserts the copies after frame 47 and fills them for issues 3 and 4;
  * clones the issue-3 elaboration (frame 44) once, inserts the copy right after
    it, and fills it with the part of the argument the elaboration only states
    in passing: why a fourth power appears at all, why it is a boundary term and
    not a second conduction term, and the one case where radiation legitimately
    joins a conduction term (an optically thick, participating medium, where the
    Rosseland conductivity grows as T^3).

Every number and every citation on the new frames:

  * the wall residual and its terms: stellarorion_physics.adb 2601-2613, with
    the quartic evaluated at 2613; the four AXIOM C1/C5 comments sit at
    2602-2612;
  * q = sigma*T^4 and the pi^4/90 moment: CurrentThesisFinalReport/appendix.tex
    784-820 (Planck's law and the Stefan-Boltzmann law);
  * T_surf = (q/(eps*sigma))^(1/4): chapter_03_methodology.tex 425-431;
  * 143,760 = 140,399 + 3,362 W/m^2 and 417 W/m^2 per kelvin at 1,348 K:
    frame 44, recomputed in proofs/fourth_power.lean (4*1348^3 = 9,797,824,768
    scaled; (1349^4 - 1348^4) = 9,808,732,785 scaled);
  * the Rosseland conductivity 16*sigma*T^3/(3*kappa*rho):
    Kaepylae 2017, Living Reviews in Computational Astrophysics, Eq. (5),
    fetched to ~/Downloads/kaepyla_2017_radiative_conductivity.html;
  * GA_Config: stellarorion_optimization.ads 211-216 (population 50, mutation
    0.1, crossover 0.7, two elites, tournament 3) and seed 42 at line 229; the
    operators at .adb 1373 (tournament), 1460 (BLX-alpha), 1621 (mutation).

Typography and geometry are inherited from the cloned slides, not set here: the
shapes keep their font, size and rectangles, and only the run text changes.
"""
import json
import pathlib
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent.parent
TOOLS = HERE / "tools"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TOOLS))

import add_issue_slides as AIS  # ruff: ignore[module-import-not-at-top-of-file]  # pyrefly: ignore [missing-import]
from pptx import Presentation  # ruff: ignore[module-import-not-at-top-of-file]

DECK = HERE / "ProgressReport.pptx"
SPEC = HERE / "scaffold.json"

CHECK_TEMPLATE = 46          # "DOES THAT SOLVE ISSUE 1?"
ISSUE_TEMPLATE = 44          # "PREVIOUS ISSUE 3: THE FOURTH POWER ..."

THEOREM: dict[str, Any] = {
    "id": "recall-issue-3-theorem",
    "source_prefix": "recall-previous-issue-3",
    "insert_at": 45,
    "title": "WHY T^4 SITS OUTSIDE FOURIER",
    "subtitle": "Issues: Issue 3, where the fourth power comes from",
    "cards": [
        ("Where the fourth power is born:",
         "Planck's spectral exitance integrated over every frequency gives q = sigma*T^4; the fourth "
         "power is the moment of x^3/(e^x - 1), pi^4/15, with zeta(4) = pi^4/90. It is an integral, "
         "not a fitted exponent."),
        ("Why it is not a second conduction term:",
         "Fourier carries heat into the stack; Stefan-Boltzmann carries it out to space. At one wall "
         "node these are two parallel sinks sharing one T, each counted once: (T - T_back)/R + "
         "eps*sigma*(T^4 - T_inf^4) = q_w. Folding sigma*T^4 into k would spend the same photons twice."),
        ("When radiation does join the conduction term:",
         "Only when the gas absorbs and re-emits, so the flux diffuses: q_rad = -(16*sigma*T^3/"
         "(3*kappa_R))*grad T, a conductivity growing as T^3 whose potential is "
         "(4*sigma/(3*kappa_R))*T^4. The DSMC gas is free-molecular and optically thin, so this term "
         "vanishes here."),
        ("What the solve then faces:",
         "f(T) = (T - T_back)/R + eps*sigma*(T^4 - T_inf^4) - q_w + G*T - S. The slope "
         "1/R + 4*eps*sigma*T^3 + G is positive, so the root is unique; that 4*eps*sigma*T^3 is the "
         "tangent of the same quartic, 417 W/m2 per kelvin at 1,348 K, not a new term."),
    ],
    "footer": "One radiative term at the wall, one conductive term through the stack, two parallel paths at one node.",
    "target": "the slide right after the elaboration of the third issue.",
    "note": "Why the deck's conduction frame carries a fourth power and why that is not a second "
            "radiative term: the quartic is the Stefan-Boltzmann boundary flux, the conduction term "
            "carries the same flux through the solid, and a Rosseland term would appear only for an "
            "optically thick participating gas.",
}

CHECKS: list[dict[str, Any]] = [
    {
        "id": "recall-issue-check-3",
        "insert_at": 48,
        "title": "DOES THAT SOLVE ISSUE 3?",
        "subtitle": "Issues: Check 3",
        "cards": [
            ("Claim:",
             "The fourth power is accounted for: it is the radiative boundary flux, counted once, and "
             "the frame says where it comes from, where it does not belong, and what it forces."),
            ("Evidence:",
             "Ada residual, stellarorion_physics.adb 2601-2613, terms C1 to C5 with the quartic at "
             "2613; thesis appendix derives q = sigma*T^4; design point 143,760 = 140,399 + 3,362 W/m2."),
            ("Verdict:",
             "Solved: one radiative term at the surface, one conductive term through the stack, a "
             "unique root, and 1,348 K recovered from (q_rad/(eps*sigma))^(1/4)."),
            ("Residual:",
             "No participating-medium radiation and no ablation: a Rosseland term would be needed only "
             "for an optically thick gas, which the free-molecular DSMC flow is not."),
        ],
        "footer": "The third previous issue, checked against the deck as it stands. The narration stays editable in PowerPoint.",
        "target": "the slide after the second check, where the third resolution is judged.",
        "note": "The third issue, checked: the fourth power is a boundary flux counted once, the "
                "iteration is forced by its quartic, and the only model that would put radiation "
                "inside a conduction term is absent because the gas is optically thin.",
    },
    {
        "id": "recall-issue-check-4",
        "insert_at": 49,
        "title": "DOES THAT SOLVE ISSUE 4?",
        "subtitle": "Issues: Check 4",
        "cards": [
            ("Claim:",
             "Every genetic parameter states its value and the job it does, and the arithmetic behind "
             "each value can be followed on the frame."),
            ("Evidence:",
             "GA_Config, stellarorion_optimization.ads 211-216 and seed 42 at 229; tournament at .adb "
             "1373, BLX-alpha at 1460, Gaussian mutation at 1621; 50 x 38 = 1,900 evaluations."),
            ("Verdict:",
             "Solved as documentation: each number traces to a line of the Ada source and to an "
             "operator the campaign actually runs."),
            ("Residual:",
             "One seed and one campaign: no convergence proof, no sensitivity sweep, and no claim that "
             "50 by 200 is the best budget."),
        ],
        "footer": "The fourth previous issue, checked against the deck as it stands. The narration stays editable in PowerPoint.",
        "target": "the slide after the third check, where the fourth resolution is judged.",
        "note": "The fourth issue, checked: the genetic settings are documented against GA_Config and "
                "the operator lines, with the evaluation budget shown, and the weakness stated rather "
                "than hidden.",
    },
]


def clone(template_index, insert_at, source_prefix, new_id, prs):
    """Clone a slide, move it into place, and rename its slots to the new id."""
    template = prs.slides[template_index]
    slide = prs.slides.add_slide(template.slide_layout)
    AIS.clone_shapes(template, slide)
    sld_ids = prs.slides._sldIdLst
    new_id_el = list(sld_ids)[-1]
    sld_ids.remove(new_id_el)
    sld_ids.insert(insert_at, new_id_el)
    renamed = 0
    for shape in slide.shapes:
        name = str(shape.name)
        if source_prefix in name:
            shape._element.nvSpPr.cNvPr.set("name", name.replace(source_prefix, new_id))
            renamed += 1
    return slide, renamed


def _tf(shape: Any) -> Any:
    """Return a shape's text frame without asking the type checker to guess."""
    return shape.text_frame


def fill(slide, frame):
    title = next(s for s in slide.shapes if str(s.name) == "frame_title")
    _tf(title).paragraphs[0].runs[0].text = frame["title"]
    sub = next(s for s in slide.shapes if str(s.name) == f"subtitle:{frame['id']}")
    _tf(sub).paragraphs[0].runs[0].text = frame["subtitle"]
    foot = next(s for s in slide.shapes if str(s.name) == "slot_footer")
    _tf(foot).paragraphs[0].runs[0].text = frame["footer"]
    for r in _tf(foot).paragraphs[0].runs[1:]:
        r._r.getparent().remove(r._r)
    lead = next(s for s in slide.shapes if str(s.name) == f"slot:{frame['id']}")
    cards = sorted((s for s in slide.shapes if str(s.name).startswith(f"card:{frame['id']}#")),
                   key=lambda s: str(s.name))
    slots = [lead] + cards
    assert len(slots) == 4, f"{frame['id']}: expected four slots, found {len(slots)}"
    for shape, (label, body) in zip(slots, frame["cards"]):
        AIS.set_para_text(shape, label, body)
    body_lines = [f"- {label} {body}" for label, body in frame["cards"]]
    body = AIS.write_notes(slide, frame, body_lines)
    return body


def visible(slide, fid):
    parts = [" ".join("".join(r.text for r in p.runs) for p in sh.text_frame.paragraphs)
             for sh in slide.shapes if str(sh.name).startswith((f"slot:{fid}", f"card:{fid}"))]
    return " ".join(parts)


def main():
    prs = Presentation(str(DECK))
    spec = json.loads(SPEC.read_text())

    existing = {str(s.name) for sl in prs.slides for s in sl.shapes}
    if any(f"slot:{fr['id']}" in existing for fr in CHECKS + [THEOREM]):
        print("  the three frames are already present; nothing to insert")
        return

    # the checks go in first, from the lower index up, then the theorem frame
    for frame in CHECKS:
        slide, renamed = clone(CHECK_TEMPLATE, frame["insert_at"], "recall-issue-check-1", frame["id"], prs)
        body = fill(slide, frame)
        print(f"  check inserted at {frame['insert_at']}: {frame['title']} | {renamed} shapes renamed | {len(body)} chars")

    slide, renamed = clone(ISSUE_TEMPLATE, THEOREM["insert_at"], THEOREM["source_prefix"], THEOREM["id"], prs)
    body = fill(slide, THEOREM)
    print(f"  theorem frame inserted at {THEOREM['insert_at']}: {THEOREM['title']} | {renamed} shapes renamed | {len(body)} chars")

    # the deck now has three more frames; the check-1 card counts them
    scaffold_total = len(spec["frames"]) + 3
    for index, slide_ in enumerate(prs.slides):
        hit = [s for s in slide_.shapes
               if getattr(s, "has_text_frame", False) and "fifty-six frames traced" in _tf(s).text]
        for shape in hit:
            for para in _tf(shape).paragraphs:
                for run in para.runs:
                    run.text = run.text.replace("fifty-six frames traced", f"{scaffold_total} frames traced")
            print(f"  slide {index}: the traced-frame count is now {scaffold_total}")

    # resync those frames' notes so the recorded body still equals the visible text
    resync = (42, 47)
    for index, slide_ in enumerate(prs.slides):
        if index not in resync:
            continue
        names = [str(s.name) for s in slide_.shapes]
        fid = next((f["id"] for f in spec["frames"] if f"slot:{f['id']}" in names), None)
        if fid is None:
            continue
        frame = dict(next(f for f in spec["frames"] if f["id"] == fid))
        frame["target"] = frame.get("target_position", "where it sits in the deck")
        body_lines = [line.strip() for line in visible(slide_, fid).split("- ") if line.strip()]
        AIS.write_notes(slide_, frame, body_lines)
        print(f"  slide {index} ({fid}): notes resynced, {len(visible(slide_, fid))} chars visible")

    # scaffold: put the three new frames where the slides are
    def insert_after(anchor, entry):
        idx = next(i for i, f in enumerate(spec["frames"]) if f["id"] == anchor)
        spec["frames"].insert(idx + 1, entry)

    insert_after("recall-previous-issue-3", {
        "id": THEOREM["id"], "section": "RECALL", "title": THEOREM["title"],
        "body": "\n".join(f"- {label} {body}" for label, body in THEOREM["cards"]),
        "target_position": THEOREM["target"], "figure": None, "note": THEOREM["note"],
        "cards_only": True, "footer": THEOREM["footer"], "subsection": THEOREM["subtitle"],
    })
    for frame in CHECKS:
        insert_after("recall-issue-check-2" if frame is CHECKS[0] else "recall-issue-check-3", {
            "id": frame["id"], "section": "RECALL", "title": frame["title"],
            "body": "\n".join(f"- {label} {body}" for label, body in frame["cards"]),
            "target_position": frame["target"], "note": frame["note"],
            "footer": frame["footer"], "cards_only": True, "subsection": frame["subtitle"],
        })

    prs.save(str(DECK))
    indent = 2 if SPEC.read_text().startswith('{\n  "') else 4
    SPEC.write_text(json.dumps(spec, indent=indent, ensure_ascii=False) + "\n")
    print(f"  saved: {len(prs.slides)} slides, {len(spec['frames'])} scaffold frames")


if __name__ == "__main__":
    main()
