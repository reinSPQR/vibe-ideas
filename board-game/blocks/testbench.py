#!/usr/bin/env python3
"""testbench.py — every golden block, built for real and put through gate.py.

    .venv/bin/python board-game/blocks/testbench.py

A block is only golden if the gate that judges products also passes it. So
this does not assert on the library's internals; it writes a real project per
block, builds it through cadcode, and requires GATE PASS. If a threshold in
gate.py tightens, the blocks have to earn their place again — which is the
point.

improve.py must see ALL PASS here before any change is kept.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
GATE = REPO_ROOT / "board-game" / "tools" / "gate.py"
ERGO = REPO_ROOT / "board-game" / "tools" / "ergonomics_check.py"
PY = REPO_ROOT / ".venv" / "bin" / "python"

# --- one fixture per block -------------------------------------------------

FAMILY = """import cadquery as cq
from blocks import shared_positions, add_piece_family

def gen_step():
    asm = cq.Assembly()
    token = cq.Workplane("XY").cylinder(6, 10)
    add_piece_family(asm, token, shared_positions(4, 3, 30), "token")
    return asm
"""

WELLS = """import cadquery as cq
from blocks import shared_positions, add_piece_family, cut_wells

BOARD_T = 8.0

def gen_step():
    # ONE position list feeds both the wells and the pieces that sit in them.
    seats = shared_positions(4, 3, 40)
    board = cq.Workplane("XY").box(200, 150, BOARD_T).translate((0, 0, BOARD_T / 2))
    board = cut_wells(board, seats, diameter=26, depth=5, top_z=BOARD_T)
    asm = cq.Assembly()
    asm.add(board, name="board")
    token = cq.Workplane("XY").cylinder(10, 10)
    add_piece_family(asm, token, seats, "token", lift=BOARD_T)
    return asm
"""

SEATED = """import cadquery as cq
from blocks import seated_pair

PEG_D, HOLE_D = seated_pair(10.0)
assert HOLE_D > PEG_D, "the seat must be larger than the piece"
assert HOLE_D - PEG_D < 1.0, "a 4x-clearance seat means both halves drifted"

def gen_step():
    asm = cq.Assembly()
    plate = cq.Workplane("XY").box(80, 80, 10).translate((0, 0, 5))
    plate = plate.cut(cq.Workplane("XY").cylinder(10, HOLE_D / 2).translate((0, 0, 5)))
    asm.add(plate, name="plate")
    asm.add(cq.Workplane("XY").cylinder(20, PEG_D / 2), name="peg_01",
            loc=cq.Location(cq.Vector(0, 0, 10)))
    return asm
"""

TILED = """import cadquery as cq
from blocks import tiled_board

def gen_step():
    asm = cq.Assembly()
    for tile in tiled_board(500, 300, 8):
        asm.add(cq.Workplane("XY").box(tile["w"] - 0.4, tile["d"] - 0.4, tile["t"]),
                name=tile["name"],
                loc=cq.Location(cq.Vector(tile["x"], tile["y"], 0)))
    return asm
"""

CASES = [
    ("add_piece_family", FAMILY, [{"name": "token", "qty": 12}]),
    ("cut_wells", WELLS, [{"name": "board", "qty": 1}, {"name": "token", "qty": 12}]),
    ("seated_pair", SEATED, [{"name": "plate", "qty": 1}, {"name": "peg", "qty": 1}]),
    ("tiled_board", TILED, [{"name": "board_tile", "qty": 6}]),
]

# The wells block exists to satisfy R2, so it is held to R2 as well as to the
# gate: a seat a hand cannot reach into is not a golden block.
WELLS_BRIEF = {"parts": [
    {"name": "token", "kind": "loose_piece", "bbox_mm": [20, 20, 10]},
    {"name": "board", "kind": "board", "bbox_mm": [200, 150, 8],
     "recesses": [{"holds": "token", "width_mm": 26, "depth_mm": 5, "count": 12}]},
]}


def python() -> str:
    return str(PY) if PY.is_file() else sys.executable


def run_case(tmp: Path, name: str, source: str, bill: list) -> tuple[bool, list]:
    home = tmp / name
    home.mkdir(parents=True)
    (home / "main.py").write_text(source, encoding="utf-8")
    # Blocks are copied INTO the project, never imported across the repo: a
    # shipped project has to stay reproducible after the library moves on.
    shutil.copy2(HERE / "blocks.py", home / "blocks.py")
    (home / "bill.json").write_text(json.dumps({"components": bill}), encoding="utf-8")
    subprocess.run([python(), str(GATE), str(home), "--bill", str(home / "bill.json"),
                    "--no-slice"], capture_output=True, text=True, timeout=900)
    report = json.loads((home / "gate.json").read_text(encoding="utf-8"))
    return bool(report.get("pass")), report.get("fails") or []


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, source, bill in CASES:
            passed, fails = run_case(tmp, name, source, bill)
            if passed:
                print(f"  ok  {name}")
            else:
                failures.append(f"{name}: GATE FAIL {fails}")

        brief = tmp / "wells_brief.json"
        brief.write_text(json.dumps(WELLS_BRIEF), encoding="utf-8")
        r = subprocess.run([python(), str(ERGO), str(brief)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            print("  ok  cut_wells/ergonomics")
        else:
            failures.append(f"cut_wells/ergonomics: {r.stdout.strip()}")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"\nALL PASS ({len(CASES) + 1} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
