#!/usr/bin/env python3
"""test_gate.py — regression fixtures for the acceptance gate.

    .venv/bin/python board-game/tools/test_gate.py

Every case here exists because the gate got it wrong once. Prints ALL PASS or
the failing cases; exit 0/1. improve.py must see ALL PASS before any change to
gate.py is kept.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GATE = HERE / "gate.py"
PY = REPO_ROOT / ".venv" / "bin" / "python"

# (name, source, bill, expect_pass, substrings that must appear in fails)
CASES = [
    (
        "separate_pieces",
        """import cadquery as cq
def gen_step():
    asm = cq.Assembly()
    for i in range(4):
        asm.add(cq.Workplane("XY").box(40, 40, 4), name=f"tile_{i+1:02d}",
                loc=cq.Location(cq.Vector(i * 45, 0, 0)))
    return asm
""",
        [{"name": "tile", "qty": 4}],
        True, [],
    ),
    (
        # The failure that destroyed turns 11-15: pieces the rules need loose
        # arriving welded into one body.
        "fused_mat",
        """import cadquery as cq
def gen_step():
    mat = cq.Workplane("XY").box(40, 40, 4)
    for i in range(1, 4):
        mat = mat.union(cq.Workplane("XY").box(40, 40, 4).translate((i * 40, 0, 0)))
    return mat
""",
        [{"name": "tile", "qty": 4}],
        False, ["unioned together"],
    ),
    (
        # A single-piece game is legitimate, and cadcode collapses a one-child
        # assembly to an unnamed model — that must not read as fusion.
        "single_piece_is_fine",
        """import cadquery as cq
def gen_step():
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(120, 120, 8), name="board")
    return asm
""",
        [{"name": "board", "qty": 1}],
        True, [],
    ),
    (
        "over_bed",
        """import cadquery as cq
def gen_step():
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(300, 300, 10), name="board")
    return asm
""",
        [{"name": "board", "qty": 1}],
        False, ["envelope", "does not fit"],
    ),
    (
        "part_in_two_lumps",
        """import cadquery as cq
def gen_step():
    asm = cq.Assembly()
    two = cq.Workplane("XY").box(20, 20, 4).union(
        cq.Workplane("XY").box(20, 20, 4).translate((100, 0, 0)))
    asm.add(two, name="token_01")
    return asm
""",
        [{"name": "token", "qty": 1}],
        False, ["disconnected bodies"],
    ),
    (
        # A lid modelled resting on its box has its whole underside facing
        # down; measuring as-modelled would fail a part that prints fine
        # flipped over.
        "orientation_is_chosen_not_assumed",
        """import cadquery as cq
def gen_step():
    asm = cq.Assembly()
    lid = cq.Workplane("XY").box(80, 60, 3).faces("<Z").workplane().rect(
        74, 54).extrude(6)
    asm.add(lid, name="lid")
    return asm
""",
        [{"name": "lid", "qty": 1}],
        True, [],
    ),
    (
        # Graduated lesson: a blanket fillet over every edge direction makes
        # OCCT build spherical vertex blends that tessellate into phantom
        # slivers. It must fail on the source, not wait for the mesh.
        "blanket_fillet_lint",
        """import cadquery as cq
def gen_step():
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(40, 40, 20).edges().fillet(2), name="block")
    return asm
""",
        [{"name": "block", "qty": 1}],
        False, ["lint", "blanket"],
    ),
]


def run_case(tmp: Path, name: str, source: str, bill: list) -> tuple[bool, list]:
    home = tmp / name
    home.mkdir(parents=True)
    (home / "main.py").write_text(source, encoding="utf-8")
    (home / "bill.json").write_text(json.dumps({"components": bill}), encoding="utf-8")
    python = str(PY) if PY.is_file() else sys.executable
    subprocess.run([python, str(GATE), str(home / "main.py"),
                    "--bill", str(home / "bill.json"), "--no-slice"],
                   capture_output=True, text=True, timeout=600)
    report = json.loads((home / "gate.json").read_text(encoding="utf-8"))
    return bool(report.get("pass")), report.get("fails") or []


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, source, bill, expect_pass, needles in CASES:
            passed, fails = run_case(tmp, name, source, bill)
            blob = " ".join(fails).lower()
            missing = [n for n in needles if n.lower() not in blob]
            if passed != expect_pass:
                failures.append(f"{name}: expected {'PASS' if expect_pass else 'FAIL'}, "
                                f"got {'PASS' if passed else 'FAIL'} ({fails})")
            elif missing:
                failures.append(f"{name}: verdict right but reason missing {missing} "
                                f"in {fails}")
            else:
                print(f"  ok  {name}")
    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"\nALL PASS ({len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
