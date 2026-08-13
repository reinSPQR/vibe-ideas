"""Counting trough board (380x170x24 mm) with 48 loose seed-weights.

One rigid rustic-chunky slab with a 4 mm rolled bullnose top edge, twelve
Ø26x16 counting wells (each with a 2 mm rim fillet and an engraved capacity
ring 9 mm up from the floor), and two Ø55x20 store wells in the short ends.
Forty-eight loose seed-weight cylinders (7 mm tall; 16 each at Ø10/Ø14/Ø18,
1 mm chamfer on both rims) drop into the wells with a continuous air gap.
All 49 parts are discrete, freely liftable bodies.
"""

import cadquery as cq

# ---------------------------------------------------------------- board
BOARD_L, BOARD_W, BOARD_H = 380.0, 170.0, 24.0   # exact overall envelope
BULLNOSE_R = 4.0                                 # rolled top-edge bullnose
CORNER_R = 8.0                                   # eased vertical corners (rustic)

SMALL_WELL_D, SMALL_WELL_DEPTH = 26.0, 16.0
STORE_WELL_D, STORE_WELL_DEPTH = 55.0, 20.0
RIM_FILLET = 2.0                                 # rounded rim on every well

RING_W, RING_DEPTH, RING_H = 1.0, 0.5, 9.0       # capacity groove: 1 wide, 0.5 deep, 9 up

SMALL_COLS = [-100.0, -60.0, -20.0, 20.0, 60.0, 100.0]
SMALL_ROWS = [35.0, -35.0]
STORE_X = 155.0

# ------------------------------------------------------------ seed-weights
WEIGHT_H = 7.0
WEIGHT_CHAMFER = 1.0
WEIGHT_DIAS = [10.0, 14.0, 18.0]                 # 16 of each = 48 total
SIZE_NAME = {10.0: "small", 14.0: "medium", 18.0: "large"}

BOARD_COLOR = cq.Color(0.42, 0.30, 0.20)
WEIGHT_COLORS = {
    10.0: cq.Color(0.82, 0.68, 0.44),
    14.0: cq.Color(0.72, 0.56, 0.34),
    18.0: cq.Color(0.55, 0.40, 0.26),
}

PART_DESCRIPTIONS = {
    "trough_board": "Single rigid slab: 12 small counting wells (with capacity "
                    "rings) in two rows of 6, 2 store wells in the short ends, "
                    "4 mm bullnose top edge.",
}


def small_centers():
    """12 small-well centers, two parallel rows of 6."""
    return [(x, y) for y in SMALL_ROWS for x in SMALL_COLS]


def build_board():
    small_floor = BOARD_H - SMALL_WELL_DEPTH     # 8.0
    store_floor = BOARD_H - STORE_WELL_DEPTH     # 4.0
    sr = SMALL_WELL_D / 2.0

    b = cq.Workplane("XY").box(BOARD_L, BOARD_W, BOARD_H, centered=(True, True, False))
    b = b.edges("|Z").fillet(CORNER_R)           # ease the 4 vertical corners
    b = b.faces(">Z").edges().fillet(BULLNOSE_R)  # rolled bullnose along full top edge

    # subtract the 12 small wells
    for (x, y) in small_centers():
        b = b.cut(cq.Solid.makeCylinder(sr, SMALL_WELL_DEPTH, cq.Vector(x, y, small_floor)))
    # subtract the 2 store wells
    for x in (-STORE_X, STORE_X):
        b = b.cut(cq.Solid.makeCylinder(STORE_WELL_D / 2.0, STORE_WELL_DEPTH,
                                        cq.Vector(x, 0.0, store_floor)))

    # rounded rim on every well opening: the large-radius circular edges of the top face
    rim_edges = [e for e in b.faces(">Z").edges("%CIRCLE").vals() if e.radius() > 9.0]
    b = b.newObject(rim_edges).fillet(RIM_FILLET)

    # engrave the capacity ring into the interior wall of the 12 small wells only
    z0 = small_floor + RING_H - RING_W / 2.0     # groove band bottom (z = 16.5)
    for (x, y) in small_centers():
        outer = cq.Solid.makeCylinder(sr + RING_DEPTH, RING_W, cq.Vector(x, y, z0))
        inner = cq.Solid.makeCylinder(sr, RING_W, cq.Vector(x, y, z0))
        b = b.cut(outer.cut(inner))

    return b


def make_weight(dia):
    """A plain right-circular cylinder, 7 mm tall, 1 mm chamfer on both rims."""
    w = cq.Workplane("XY").cylinder(WEIGHT_H, dia / 2.0, centered=(True, True, False))
    return w.edges("%CIRCLE").chamfer(WEIGHT_CHAMFER)


def validate(board):
    bb = board.val().BoundingBox()
    for axis, got, exp in (("L", bb.xlen, BOARD_L), ("W", bb.ylen, BOARD_W), ("H", bb.zlen, BOARD_H)):
        assert abs(got - exp) < 1e-4, f"board {axis} = {got:.5f} != {exp}"
    # loose-fit proof: largest weight in the smallest well keeps a continuous air gap
    gap = SMALL_WELL_D / 2.0 - max(WEIGHT_DIAS) / 2.0
    assert gap >= 3.0, f"radial clearance {gap} mm < 3 mm minimum"


def gen_step():
    board = build_board()
    validate(board)

    asm = cq.Assembly()
    asm.add(board, name="trough_board", color=BOARD_COLOR)

    counts = {d: 0 for d in WEIGHT_DIAS}

    def add_weight(dia, loc):
        counts[dia] += 1
        asm.add(make_weight(dia), name=f"seed_{SIZE_NAME[dia]}_{counts[dia]:02d}",
                color=WEIGHT_COLORS[dia], loc=cq.Location(loc))

    # 12 seed-weights resting loose in the small wells (hero placement, sizes mixed)
    small_floor = BOARD_H - SMALL_WELL_DEPTH
    for i, (x, y) in enumerate(small_centers()):
        add_weight(WEIGHT_DIAS[i % 3], cq.Vector(x, y, small_floor))

    # remaining 36 staged upright beside the board, grouped by size, spaced clear
    stage_cols = [(c - 5.5) * 24.0 for c in range(12)]
    stage_rows = {10.0: -108.0, 14.0: -140.0, 18.0: -172.0}
    for dia in WEIGHT_DIAS:
        for x in stage_cols:
            add_weight(dia, cq.Vector(x, stage_rows[dia], 0.0))

    assert all(v == 16 for v in counts.values()), f"weight counts wrong: {counts}"
    return asm
