#!/usr/bin/env python3
"""audit.py — what the pipeline could still do to itself, now that it has no
score to inflate.

    python3 board-game/tools/audit.py
    python3 board-game/tools/audit.py --baseline    # re-record the thresholds

The old audit had ten checks. Seven of them existed because a remote service
produced the artifacts and a rubric produced a number, so provenance and
score-consistency had to be proven. Neither is true any more: builds happen
here, git records who changed what, and nothing is scored. Keeping those
checks would have been theatre.

Four risks survive the change, and one of them is new:

1. GATE EROSION (new, and the important one). With acceptance reduced to a
   deterministic gate, the cheapest way to make everything pass is to move
   the gate. This compares the live thresholds against a recorded baseline
   and flags any LOOSENING — direction matters, so tightening is silent.
2. SHIPPED WITHOUT MEASUREMENT. Nothing may reach `shipped` without a
   `gate.json` that actually passed. This is the one invariant the whole
   rebuild rests on.
3. DEGENERACY. Optimising for pass rate rewards proposing simpler games. If
   part families, piece counts, and relief depths drift down over time, the
   loop is getting better at the metric rather than at board games.
4. PROMPT BLOAT. Agents that rewrite their own instructions grow them without
   limit; a Learned Heuristics section that doubles is one nobody reads.

Exit 0 green, 1 amber, 2 red.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "board-game" / "tools"
AGENTS = REPO_ROOT / ".claude" / "agents"
IDEAS = REPO_ROOT / "board-game" / "ideas"
QUEUE = REPO_ROOT / "board-game" / "QUEUE.json"
BASELINE = TOOLS / "thresholds_baseline.json"

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"

# Which direction is a loosening for each threshold. "up" means raising the
# number makes the gate easier to pass.
LOOSER = {
    "BED_X_MM": "up", "BED_Y_MM": "up", "BED_Z_MM": "up",
    "BED_MARGIN_MM": "down",
    "OVERHANG_FAIL_PCT": "up", "BRIDGE_SPAN_MAX_MM": "up",
    "MIN_BODY_VOLUME_MM3": "up",
    "MIN_GRASP_MM": "down", "MIN_PROTRUSION_MM": "down",
    "FINGER_ROOM_MM": "down", "MIN_SEAT_CLEARANCE_MM": "down",
    "MAX_STACK_ASPECT": "up", "MIN_RELIEF_MM": "down",
    "REPAIR_BUDGET": "up",
}

HEURISTICS_WORD_CAP = 1200


def live_thresholds() -> dict:
    sys.path.insert(0, str(TOOLS))
    import ergonomics_check
    import gate
    import queue as queue_mod

    values = {}
    for module in (gate, ergonomics_check, queue_mod):
        for name in LOOSER:
            if hasattr(module, name):
                values[name] = getattr(module, name)
    return values


def check_gate_erosion(findings: list) -> None:
    live = live_thresholds()
    if not BASELINE.is_file():
        findings.append((AMBER, "erosion", "no threshold baseline recorded — run "
                                           "--baseline once so drift becomes visible"))
        return
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    for name, value in sorted(live.items()):
        if name not in base:
            findings.append((AMBER, "erosion", f"{name} is new since the baseline"))
            continue
        was, direction = base[name], LOOSER[name]
        if (direction == "up" and value > was) or (direction == "down" and value < was):
            findings.append((RED, "erosion",
                             f"{name} moved {was} -> {value}, which makes the gate "
                             f"EASIER to pass. A threshold may only be loosened by a "
                             f"human through a PR, with a reason"))
        elif value != was:
            print(f"  note: {name} tightened {was} -> {value}")


def check_shipped_were_measured(findings: list) -> None:
    if not QUEUE.is_file():
        return
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    for slug, item in sorted(data.get("ideas", {}).items()):
        if item.get("state") != "shipped":
            continue
        report = IDEAS / slug / "project" / "gate.json"
        if not report.is_file():
            findings.append((RED, "unmeasured",
                             f"{slug} is shipped with no gate.json at all"))
            continue
        if not json.loads(report.read_text(encoding="utf-8")).get("pass"):
            findings.append((RED, "unmeasured",
                             f"{slug} is shipped but its gate.json says it failed"))


def _complexity(idea: dict) -> dict:
    components = idea.get("components") or []
    return {
        "families": len(components),
        "pieces": sum(int(c.get("qty", 0)) for c in components),
    }


def check_degeneracy(findings: list) -> None:
    """Compare the newest third of proposals against the oldest third. Not a
    strict rule — designs vary — but a sustained shrink in both families and
    piece count while the gate keeps passing is the signature of a loop
    learning to win rather than to design."""
    ideas = []
    for path in sorted(IDEAS.glob("*/idea.json")):
        try:
            ideas.append(_complexity(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    if len(ideas) < 6:
        return
    third = max(2, len(ideas) // 3)
    old, new = ideas[:third], ideas[-third:]
    for key in ("families", "pieces"):
        was = sum(i[key] for i in old) / len(old)
        now = sum(i[key] for i in new) / len(new)
        if was and now < was * 0.6:
            findings.append((AMBER, "degeneracy",
                             f"average {key} per idea fell {was:.1f} -> {now:.1f} "
                             f"across the queue's history — check that the ideator "
                             f"is not simply proposing easier builds"))


def check_prompt_bloat(findings: list) -> None:
    for path in sorted(AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"#+\s*Learned Heuristics(.*)$", text,
                          re.S | re.I)
        if not match:
            continue
        words = len(match.group(1).split())
        if words > HEURISTICS_WORD_CAP:
            findings.append((AMBER, "bloat",
                             f"{path.name}: Learned Heuristics is {words} words "
                             f"(cap {HEURISTICS_WORD_CAP}) — an agent that keeps "
                             f"appending eventually reads none of it"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baseline", action="store_true",
                    help="record the current thresholds as the baseline")
    args = ap.parse_args()

    if args.baseline:
        values = live_thresholds()
        BASELINE.write_text(json.dumps(values, indent=2, sort_keys=True),
                            encoding="utf-8")
        print(f"recorded {len(values)} thresholds to {BASELINE.name}")
        return 0

    findings: list[tuple[str, str, str]] = []
    check_gate_erosion(findings)
    check_shipped_were_measured(findings)
    check_degeneracy(findings)
    check_prompt_bloat(findings)

    if not findings:
        print("AUDIT GREEN")
        return 0
    level = RED if any(f[0] == RED for f in findings) else AMBER
    print(f"AUDIT {level}")
    for lvl, check, detail in findings:
        print(f"  [{lvl}] {check}: {detail}")
    return 2 if level == RED else 1


if __name__ == "__main__":
    sys.exit(main())
