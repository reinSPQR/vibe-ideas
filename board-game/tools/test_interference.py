#!/usr/bin/env python3
"""test_interference.py — regression fixtures for the interference check.

    .venv/bin/python board-game/tools/test_interference.py

Every case is geometry whose answer is known by arithmetic, not by looking at a
render, so the measured volume can be checked against the number a human would
compute. Prints ALL PASS or the failing cases; exit 0/1.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cadquery as cq  # noqa: E402

from interference import check_interference  # noqa: E402

TOLERANCE_PCT = 12.0


def export(asm: cq.Assembly, tag: str) -> Path:
    path = Path(tempfile.mkdtemp()) / f"{tag}.stl"
    cq.exporters.export(asm.toCompound(), str(path))
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def case_far_apart():
    """Two cubes 20mm apart. The broad phase should never hand this to the
    narrow phase at all."""
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(20, 20, 20), name="a")
    asm.add(cq.Workplane("XY").box(20, 20, 20), name="b",
            loc=cq.Location(cq.Vector(40, 0, 0)))
    return export(asm, "far_apart"), 2, True, 0.0


def case_known_overlap():
    """Two 20mm cubes offset 15mm: they share a 5 x 20 x 20 slab = 2000mm3."""
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(20, 20, 20), name="a")
    asm.add(cq.Workplane("XY").box(20, 20, 20), name="b",
            loc=cq.Location(cq.Vector(15, 0, 0)))
    return export(asm, "known_overlap"), 2, False, 5.0 * 20.0 * 20.0


def case_peg_through_plate():
    """THE case the whole module exists for.

    A 10mm peg driven straight through a solid 6mm plate. No vertex of either
    solid is inside the other — the peg's vertices are all on its two end rings,
    above and below the plate; the plate's are outside the peg's radius — so
    vertex-containment, which is what a general-purpose collision helper uses,
    reports nothing at all. This is the shape of the Armillary defect (a tile's
    knob standing in the path of a mask disc) and of every peg-in-hole,
    tab-in-slot and pin-in-bore a board game has.

    Shared volume is the peg's cross-section times the plate thickness:
    pi * 5^2 * 6 = 471.24mm3.
    """
    import math
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(60, 60, 6), name="plate")
    asm.add(cq.Workplane("XY").circle(5).extrude(30), name="peg",
            loc=cq.Location(cq.Vector(0, 0, -15)))
    return export(asm, "peg_through_plate"), 2, False, math.pi * 25.0 * 6.0


def case_peg_in_clearance_hole():
    """The same peg through a 12mm hole: 1mm of clearance all round, which is
    a fit, not a fault. Must measure zero — this is the false-positive trap that
    a distance-based check walks straight into."""
    plate = cq.Workplane("XY").box(60, 60, 6).faces(">Z").workplane().hole(12)
    asm = cq.Assembly()
    asm.add(plate, name="plate")
    asm.add(cq.Workplane("XY").circle(5).extrude(30), name="peg",
            loc=cq.Location(cq.Vector(0, 0, -15)))
    return export(asm, "peg_in_clearance_hole"), 2, True, 0.0


def case_seated_in_round_well():
    """A disc resting on the floor of a round pocket it fits inside.

    Faces are coincident over the whole floor, which is exactly the geometry a
    distance check calls a collision. Curved walls tessellate differently on the
    two parts, so they stay separate bodies and the pair really is measured."""
    board = cq.Workplane("XY").box(60, 60, 10).faces(">Z").workplane().hole(24, 4)
    asm = cq.Assembly()
    asm.add(board, name="board")
    asm.add(cq.Workplane("XY").circle(11).extrude(4), name="disc",
            loc=cq.Location(cq.Vector(0, 0, 1)))
    return export(asm, "seated_in_round_well"), 2, True, 0.0


CASES = [
    ("far_apart", case_far_apart),
    ("known_overlap", case_known_overlap),
    ("peg_through_plate", case_peg_through_plate),
    ("peg_in_clearance_hole", case_peg_in_clearance_hole),
    ("seated_in_round_well", case_seated_in_round_well),
]


# ---------------------------------------------------------------------------
# The known limitation, asserted rather than left to be discovered
# ---------------------------------------------------------------------------

def case_coincident_faces_is_inconclusive():
    """Two cubes touching on an exactly-coincident face.

    STL carries no vertex sharing, so connectivity has to be rebuilt by welding
    vertices within a tolerance — and that welds the two parts to each other
    wherever their tessellations coincide exactly, which is what happens between
    two axis-aligned flats of the same size. The pair stops being two closed
    bodies (measured: it fragments into six open shells), so it cannot be tested.

    What must NOT happen is a quiet pass. The check has to say it could not
    measure this. Curved contact — the round-well case above — is unaffected,
    which is why Armillary's 39 pieces separate cleanly.
    """
    asm = cq.Assembly()
    asm.add(cq.Workplane("XY").box(20, 20, 20), name="a")
    asm.add(cq.Workplane("XY").box(20, 20, 20), name="b",
            loc=cq.Location(cq.Vector(20, 0, 0)))
    path = export(asm, "coincident_faces")
    report = check_interference(path, expected_components=2)
    if not report["inconclusive"]:
        return ("coincident_faces_is_inconclusive",
                f"welded/fragmented contact was NOT reported as inconclusive; "
                f"got {report['placed_components']} components, "
                f"findings={report['findings']}")
    return None


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_case(name, factory) -> str | None:
    path, expected_components, expect_pass, expected_volume = factory()
    report = check_interference(path, expected_components=expected_components)

    if report["placed_components"] != expected_components:
        return (f"{name}: expected {expected_components} placed components, "
                f"got {report['placed_components']}")

    if report["inconclusive"]:
        return f"{name}: unexpectedly inconclusive: {report['inconclusive']}"

    if report["pass"] != expect_pass:
        return (f"{name}: expected pass={expect_pass}, got pass={report['pass']} "
                f"({report['findings']})")

    measured = max((m["volume_mm3"] for m in report["measured_overlaps"]), default=0.0)
    if expected_volume == 0.0:
        if measured != 0.0:
            return f"{name}: expected no shared volume, measured {measured}mm3"
    else:
        error = abs(measured - expected_volume) / expected_volume * 100.0
        if error > TOLERANCE_PCT:
            return (f"{name}: measured {measured}mm3 vs arithmetic "
                    f"{expected_volume:.2f}mm3 ({error:.1f}% off, "
                    f"tolerance {TOLERANCE_PCT}%)")
        print(f"  {name}: {measured}mm3 vs {expected_volume:.2f}mm3 expected "
              f"({error:.1f}% off)")

    if name == "far_apart" and report["pairs_tested"] != 0:
        return f"{name}: broad phase should have pruned the only pair"

    return None


def main() -> int:
    failures = []
    for name, factory in CASES:
        try:
            failure = run_case(name, factory)
        except Exception as exc:  # a fixture that cannot build is a failure
            failure = f"{name}: raised {type(exc).__name__}: {exc}"
        if failure:
            failures.append(failure)

    try:
        limitation = case_coincident_faces_is_inconclusive()
    except Exception as exc:
        limitation = f"coincident_faces: raised {type(exc).__name__}: {exc}"
    if limitation:
        failures.append(limitation)

    if failures:
        for line in failures:
            print(f"FAIL {line}")
        return 1
    print(f"ALL PASS ({len(CASES) + 1} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
