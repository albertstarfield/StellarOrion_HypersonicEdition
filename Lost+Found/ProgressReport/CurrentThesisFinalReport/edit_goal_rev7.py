#!/usr/bin/env python3
"""edit_goal_rev7.py - raise the session page cap from 150 to 200.

AXIOMS: the persisted OpenCode Goal JSON is the single source of truth for the
page cap; user instruction ("edit the goal to be under neath of 200 page",
"we expanded it") supersedes the old 150-page clause.
THEORIES: rewrite only the three page-cap phrases, bump revision and updatedAt,
then re-load the file to prove it still parses and no 150-page wording remains.
APPLICATIONS: run with plain python3 from the thesis dir; prints revision and
verification booleans; exits 1 if any page-cap "150" wording survives.
CITATIONS: goal file .opencode/goals/01d6003573ef6db15a2689078b47b969.json,
json.load/dump pattern used for goal revisions 4-6.
"""

import json
import sys
import time
from pathlib import Path

GOAL = Path("../../../.opencode/goals/01d6003573ef6db15a2689078b47b969.json")
if not GOAL.exists():
    GOAL = Path.home() / ".config" / "opencode" / "goals" / "01d6003573ef6db15a2689078b47b969.json"

PAIRS = [
    ("LIMIT THE PAGE TO 150", "LIMIT THE PAGE TO 200"),
    ("at most 150 pages", "at most 200 pages"),
    ("page count is 150 or fewer", "page count is 200 or fewer"),
    ("at most 150", "at most 200"),
    ("150-page", "200-page"),
    ("150 page", "200 page"),
]


def fix(text):
    for old, new in PAIRS:
        text = text.replace(old, new)
    return text


raw = GOAL.read_text(encoding="utf-8")
goal = json.loads(raw)

goal["objective"] = fix(goal["objective"])
for req in goal.get("requirements", []):
    if isinstance(req, dict) and "text" in req:
        req["text"] = fix(req["text"])

goal["revision"] = int(goal.get("revision", 6)) + 1
goal["updatedAt"] = int(time.time() * 1000)

GOAL.write_text(
    json.dumps(goal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)

# Verification pass: re-parse and prove the cap wording changed everywhere.
check = json.loads(GOAL.read_text(encoding="utf-8"))
blob = json.dumps(check, ensure_ascii=False)
leftovers = [s for s in ("150 pages", "PAGE TO 150", "150 or fewer", "150-page") if s in blob]
print("revision:", check.get("revision"))
print("objective has 200:", ("200 pages" in check["objective"]) or ("PAGE TO 200" in check["objective"]))
print("requirement has 200:", any(
    isinstance(r, dict) and ("200 pages" in r.get("text", "") or "PAGE TO 200" in r.get("text", ""))
    for r in check.get("requirements", [])
))
print("leftover 150-cap wording:", leftovers if leftovers else "none")
print("status:", check.get("status"))
sys.exit(1 if leftovers else 0)
