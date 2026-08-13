#!/usr/bin/env python3
"""test_checks.py — regression fixtures for gates R1 (rules) and R2 (ergonomics).

    python3 board-game/tools/test_checks.py

No CAD, so this runs in well under a second. Prints ALL PASS or the failures.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ergonomics_check import check as ergo_check  # noqa: E402
from rules_check import check as rules_check  # noqa: E402


def _idea(**over) -> dict:
    idea = {
        "slug": "fixture", "title": "Fixture", "playtime_min": 30,
        "players": {"min": 2, "max": 4},
        "components": [{"name": "board", "qty": 1},
                       {"name": "token", "qty": 20, "per_player": 5}],
        "rules": {
            "setup": [{"text": "Lay out the board.", "uses": ["board"]}],
            "turn": [{"text": "Place a token.", "uses": ["token", "board"]}],
            "end": [{"text": "Ends when tokens run out.", "uses": ["token"]}],
            "win": {"text": "Most tokens placed wins.", "uses": ["token"]},
        },
    }
    idea.update(over)
    return idea


RULES_CASES = [
    ("clean_game", _idea(), []),
    (
        "rule_reaches_for_a_piece_that_is_not_in_the_box",
        _idea(rules={**_idea()["rules"],
                     "turn": [{"text": "Draw a stick.", "uses": ["tally_stick"]}]}),
        ["not in the component bill"],
    ),
    (
        "piece_in_the_box_that_no_rule_uses",
        _idea(components=[*_idea()["components"], {"name": "spare_dial", "qty": 1}]),
        ["no rule ever uses it"],
    ),
    (
        # "Each player takes 5" against a bill that only makes 12.
        "per_player_quantity_does_not_survive_a_full_table",
        _idea(components=[{"name": "board", "qty": 1},
                          {"name": "token", "qty": 12, "per_player": 5}]),
        ["needs 20", "only makes 12"],
    ),
    (
        "no_win_condition",
        _idea(rules={k: v for k, v in _idea()["rules"].items() if k != "win"}),
        ["rules:win: missing"],
    ),
    (
        "step_without_a_uses_list",
        _idea(rules={**_idea()["rules"], "turn": [{"text": "Do something."}]}),
        ["no `uses` list"],
    ),
]


def _brief(**over) -> dict:
    brief = {"parts": [
        {"name": "token", "kind": "loose_piece", "bbox_mm": [20, 20, 10]},
        {"name": "board", "kind": "board", "bbox_mm": [200, 200, 6],
         "recesses": [{"holds": "token", "width_mm": 22, "depth_mm": 6, "count": 12}]},
    ]}
    brief.update(over)
    return brief


ERGO_CASES = [
    ("comfortable_game", _brief(), []),
    (
        # Turn 15, Sluice Row, verbatim: 7mm seeds on the floor of 26mm-wide,
        # 16mm-deep wells. Every geometric check passed at the time.
        "piece_sunk_out_of_finger_reach",
        {"parts": [
            {"name": "seed", "kind": "loose_piece", "bbox_mm": [20, 20, 7]},
            {"name": "board", "kind": "board", "bbox_mm": [240, 120, 16],
             "recesses": [{"holds": "seed", "width_mm": 26, "depth_mm": 16}]}]},
        ["retrieve", "below the rim"],
    ),
    (
        "piece_too_small_to_pick_up",
        {"parts": [{"name": "chip", "kind": "loose_piece", "bbox_mm": [6, 6, 2]}]},
        ["grasp"],
    ),
    (
        "press_fit_seat",
        {"parts": [
            {"name": "peg", "kind": "loose_piece", "bbox_mm": [12, 12, 20]},
            {"name": "board", "kind": "board", "bbox_mm": [200, 200, 8],
             "recesses": [{"holds": "peg", "width_mm": 12.2, "depth_mm": 6}]}]},
        ["drop in rather than press in"],
    ),
    (
        # Graduated from CAD_GRAMMAR: sub-millimetre relief keeps being
        # modelled faithfully and then being invisible.
        "relief_too_shallow_to_see",
        {"parts": [{"name": "board", "kind": "board", "bbox_mm": [200, 200, 6],
                    "relief_mm": 0.5}]},
        ["relief"],
    ),
    (
        "tall_piece_topples",
        {"parts": [{"name": "obelisk", "kind": "loose_piece",
                    "bbox_mm": [10, 10, 60], "stackable": True}]},
        ["topples"],
    ),
]


def run(label: str, fn, cases) -> list:
    failures = []
    for name, payload, needles in cases:
        findings = fn(payload)
        blob = " ".join(findings).lower()
        expect_pass = not needles
        if bool(findings) == expect_pass:
            failures.append(f"{label}/{name}: expected "
                            f"{'PASS' if expect_pass else 'FAIL'}, got {findings}")
        elif missing := [n for n in needles if n.lower() not in blob]:
            failures.append(f"{label}/{name}: verdict right but reason missing "
                            f"{missing} in {findings}")
        else:
            print(f"  ok  {label}/{name}")
    return failures


def check_no_stdlib_shadowing() -> list:
    """No tool may be named after a stdlib module.

    Python puts a script's own directory at sys.path[0], so `tools/queue.py`
    shadowed the stdlib `queue` for every script in that directory. networkx
    does `from queue import PriorityQueue`, so the whole CAD gate died with an
    ImportError that named neither the queue nor the gate. Cheap to check,
    very expensive to debug.
    """
    import sys as _sys

    stdlib = getattr(_sys, "stdlib_module_names", frozenset())
    clashes = [p.name for p in Path(__file__).resolve().parent.glob("*.py")
               if p.stem in stdlib]
    return [f"shadowing/{name}: shadows a stdlib module for every script in "
            f"this directory — rename it" for name in sorted(clashes)]


def main() -> int:
    failures = run("rules", rules_check, RULES_CASES)
    failures += run("ergo", ergo_check, ERGO_CASES)
    shadowing = check_no_stdlib_shadowing()
    failures += shadowing
    if not shadowing:
        print("  ok  tools/no_stdlib_shadowing")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"\nALL PASS ({len(RULES_CASES) + len(ERGO_CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
