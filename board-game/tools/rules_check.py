#!/usr/bin/env python3
"""rules_check.py — gate R1, the mechanical half. Text only, no CAD, no LLM.

    python3 board-game/tools/rules_check.py board-game/ideas/<slug>/idea.json

Runs before the brief is written and before a single second of CAD is spent,
because a game whose rules and whose box of pieces disagree is not a modelling
problem and no amount of geometry fixes it.

It answers one question with no judgement in it: do the rules and the
component bill describe the same game? Whether the game is any *fun* is the
playability lens's job — that half is opinion and lives elsewhere.

The check is deterministic only because the schema makes it so: every rule
step declares the components it touches, in a `uses` list, by bill name.

    {
      "slug": "sluice-row",
      "title": "Sluice Row",
      "players": {"min": 2, "max": 4},
      "playtime_min": 30,
      "components": [
        {"name": "trough_board", "qty": 1, "desc": "..."},
        {"name": "seed_small",   "qty": 48, "desc": "...", "per_player": 12}
      ],
      "rules": {
        "setup": [{"text": "...", "uses": ["trough_board", "seed_small"]}],
        "turn":  [{"text": "...", "uses": ["seed_small"]}],
        "end":   [{"text": "...", "uses": []}],
        "win":   {"text": "...", "uses": ["seed_small"]}
      }
    }

Asking the ideator to write `uses` is not bureaucracy — it is the same move as
the numeric contract in the brief. A component nobody declared a use for is
almost always a component the rules forgot, and a rule reaching for a piece
that is not in the box is almost always a rule the bill forgot. Both are
invisible in prose and obvious in a list.

Exit 0 = PASS, 1 = FAIL. Prints one line plus every finding.

On a FAIL the report carries `Disposition: clarify`. Every finding this
checker can produce is a mismatch between what the rules *say* and what the
box *holds* — fixing it is a matter of making the two agree in text, and the
queue's mechanic-surface check (see `pipeline_queue.mech_surface`) verifies
after the fact that the fix stayed in the prose. If the honest fix turns out
to be a new component or a different quantity, the queue converts that round
into a paid rework automatically; this label only chooses which budget the
round *starts* in.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_PHASES = ("setup", "turn", "end", "win")


def _steps(rules: dict, phase: str) -> list:
    """Phases are lists of steps; `win` may be a single step."""
    block = rules.get(phase)
    if block is None:
        return []
    return block if isinstance(block, list) else [block]


def check(idea: dict) -> list:
    findings: list[str] = []

    components = idea.get("components") or []
    if not components:
        return ["bill: no components at all — this is not a physical game"]

    bill: dict[str, dict] = {}
    for item in components:
        name = str(item.get("name", "")).strip()
        if not name:
            findings.append("bill: a component has no name")
            continue
        if name in bill:
            findings.append(f"bill:{name}: declared twice — merge into one line")
        qty = int(item.get("qty", item.get("quantity", 0)))
        if qty <= 0:
            findings.append(f"bill:{name}: quantity {qty} is not a real count")
        bill[name] = {**item, "qty": qty}

    rules = idea.get("rules") or {}
    for phase in REQUIRED_PHASES:
        if not _steps(rules, phase):
            findings.append(f"rules:{phase}: missing — a game with no {phase} "
                            f"phase cannot be played to a conclusion")

    used: set[str] = set()
    for phase in REQUIRED_PHASES:
        for i, step in enumerate(_steps(rules, phase), 1):
            if not str(step.get("text", "")).strip():
                findings.append(f"rules:{phase}[{i}]: empty step")
            uses = step.get("uses")
            if uses is None:
                findings.append(f"rules:{phase}[{i}]: no `uses` list — every step "
                                f"must name the components it touches, even if empty")
                continue
            for name in uses:
                if name not in bill:
                    findings.append(f"rules:{phase}[{i}]: uses '{name}', which is "
                                    f"not in the component bill")
                else:
                    used.add(name)

    for name in bill:
        if name not in used:
            findings.append(f"bill:{name}: in the box but no rule ever uses it — "
                            f"either the rules forgot it or it should not be made")

    # Per-player quantities have to survive a full table. This catches the
    # classic "each player takes 5" against a bill that only makes 12.
    players = idea.get("players") or {}
    pmin, pmax = int(players.get("min", 0)), int(players.get("max", 0))
    if pmin < 1 or pmax < pmin:
        findings.append(f"players: range {pmin}-{pmax} is not a real player count")
    else:
        for name, item in bill.items():
            per = item.get("per_player")
            if per:
                needed = int(per) * pmax
                if item["qty"] < needed:
                    findings.append(
                        f"bill:{name}: {per} per player x {pmax} players needs "
                        f"{needed}, but the bill only makes {item['qty']}")

    playtime = int(idea.get("playtime_min") or 0)
    if playtime <= 0:
        findings.append("playtime_min: missing — needed to sanity-check turn count")

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("idea", type=Path)
    ap.add_argument("--out", type=Path, help="default <idea dir>/rules_check.json")
    args = ap.parse_args()

    idea = json.loads(args.idea.read_text(encoding="utf-8"))
    findings = check(idea)
    report = {"idea": str(args.idea), "pass": not findings, "findings": findings,
              "disposition": None if report["pass"] else "clarify"}
    (args.out or args.idea.parent / "rules_check.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print(("RULES PASS " if report["pass"] else "RULES FAIL ")
          + f"{len(findings)} finding(s)")
    for f in findings:
        print("  -", f)
    if not report["pass"]:
        print("Disposition: clarify")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
