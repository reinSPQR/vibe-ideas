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


def check_graduation_checker_bites() -> list:
    """The graduation checker's own sentinel.

    A checker that cannot fail is indistinguishable from one that works, right
    up to the day something breaks and it prints ALL PASS anyway. So: one claim
    that is true, and one for each way a claim can be false, run against the
    real tree through a substituted lessons file.
    """
    import tempfile

    import graduation_check as gc

    filler = " " + "x" * 60  # lessons.md only reads lines over 40 chars
    good = "- [GRADUATED -> blocks.shared_positions]" + filler
    false_claims = [
        ("missing_symbol", "- [GRADUATED -> gate.no_such_function]" + filler),
        ("unknown_module", "- [GRADUATED -> nowhere.MIN_RELIEF_MM]" + filler),
        ("absent_literal", '- [GRADUATED -> gate:"no-such-lint-rule"]' + filler),
        ("prose_not_target", "- [GRADUATED -> gate.py lint]" + filler),
    ]

    findings = []
    original = gc.LESSONS
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "lessons.md"
        try:
            gc.LESSONS = path
            path.write_text(good + "\n", encoding="utf-8")
            broken, checked, _ = gc.verify()
            if broken or checked != 1:
                findings.append(f"graduation/landed_claim: a graduation that IS in "
                                f"the tree was reported broken ({broken})")
            for label, line in false_claims:
                path.write_text(line + "\n", encoding="utf-8")
                broken, _, _ = gc.verify()
                if not broken:
                    findings.append(f"graduation/{label}: a false claim passed — "
                                    f"the checker is blind to this kind of rot")
        finally:
            gc.LESSONS = original
    return findings


def check_fix_tier_ladder_bites() -> list:
    """The tier ladder's own sentinel.

    The ladder is only worth anything if it reads a weak graduation as weak.
    Two ways it could go quietly wrong: scoring a lesson by its worst target
    instead of its best (so pairing a block with a gate check would look like
    a check), and accepting any ceiling clause at all (so `| ceiling: no` would
    buy silence forever).
    """
    import tempfile

    import graduation_check as gc

    filler = " " + "x" * 60
    long_reason = "the print bed is a fixed physical size and no upstream tier can change it"
    cases = [
        # (label, marker body, expected tier or None if it must be rejected,
        #  expected ceiling truthiness)
        ("check_only", 'gate:"blanket-fillet"', "check", False),
        ("best_of_several", "gate.check_bill, blocks.add_piece_family",
         "block", False),
        ("ceiling_accepted", f'gate:"blanket-fillet" | ceiling: {long_reason}',
         "check", True),
        ("ceiling_too_short", 'gate:"blanket-fillet" | ceiling: n/a', None, False),
        ("ceiling_malformed", 'gate:"blanket-fillet" | because reasons', None, False),
    ]

    findings = []
    original = gc.LESSONS
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "lessons.md"
        try:
            gc.LESSONS = path
            for label, body, tier, has_ceiling in cases:
                path.write_text(f"- [GRADUATED -> {body}]{filler}\n", encoding="utf-8")
                good, broken, _ = gc.scan()
                if tier is None:
                    if not broken:
                        findings.append(f"fix-tier/{label}: a ceiling clause that "
                                        f"says nothing was accepted — the escape "
                                        f"valve is free")
                    continue
                if broken or len(good) != 1:
                    findings.append(f"fix-tier/{label}: expected one graduation, "
                                    f"got {len(good)} and {broken}")
                    continue
                entry = good[0]
                if entry["tier"] != tier:
                    findings.append(f"fix-tier/{label}: scored {entry['tier']}, "
                                    f"expected {tier}")
                if bool(entry["ceiling"]) != has_ceiling:
                    findings.append(f"fix-tier/{label}: ceiling was "
                                    f"{entry['ceiling']!r}")
        finally:
            gc.LESSONS = original

    untiered = sorted(set(gc.MODULES) - set(gc.TIERS))
    if untiered:
        findings.append(f"fix-tier/every_module_has_a_tier: {untiered} can be "
                        f"graduated into but has no tier, so audit.py cannot "
                        f"say how far upstream it is")
    return findings


def main() -> int:
    failures = run("rules", rules_check, RULES_CASES)
    failures += run("ergo", ergo_check, ERGO_CASES)
    shadowing = check_no_stdlib_shadowing()
    failures += shadowing
    if not shadowing:
        print("  ok  tools/no_stdlib_shadowing")
    graduations = check_graduation_checker_bites()
    failures += graduations
    if not graduations:
        print("  ok  tools/graduation_checker_bites")
    tiers = check_fix_tier_ladder_bites()
    failures += tiers
    if not tiers:
        print("  ok  tools/fix_tier_ladder_bites")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"\nALL PASS ({len(RULES_CASES) + len(ERGO_CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
