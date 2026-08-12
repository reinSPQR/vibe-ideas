"""Two-board stacked 33-hole English peg-solitaire assembly.

70 separate bodies: 2 cross boards + 4 corner posts + 64 loose pegs.
Boards held 30 mm apart by four D10x60 posts whose stepped D8x15 pins press
into D7.85 corner bores (0.15 mm diametral interference). Display layout seats
pegs upright in most holes (both centers empty) and floats one peg on the
bottom-center axis in the open gap. Chunky / utilitarian proportions.
"""

import cadquery as cq

# ---- board -----------------------------------------------------------------
BOARD = 180.0          # overall cross bbox X and Y
T = 12.0               # board thickness
PITCH = 24.0           # peg-hole grid pitch (7 cols span 144 mm)
ARM_HALF = 36.0        # cross arm half-width = 1.5 * pitch -> 3 holes wide
HOLE_D = 12.0          # peg-hole diameter
HOLE_DEPTH = 8.0       # peg-hole blind depth (floor at 4 mm)

# ---- corner posts + bores --------------------------------------------------
POST_XY = 42.0         # post center offset in +/-X and +/-Y (inside notch)
BOSS = 16.0            # square boss filling notch corner to host the bore
POST_D = 10.0          # post barrel diameter
PIN_D = 8.0            # insertion-pin diameter
PIN_L = 15.0           # insertion-pin length (each end)
POST_L = 60.0          # post overall length
BORE_D = 7.85          # board bore = pin - 0.15 mm (press-fit interference)

# ---- pegs ------------------------------------------------------------------
PEG_D = 11.4           # peg diameter (0.3 mm radial clearance in D12 hole)
PEG_H = 20.0           # peg height

# ---- assembled stack geometry ----------------------------------------------
GAP = 30.0             # clear air gap between facing board surfaces
# bottom board top face at z=0 -> body z[-12,0]; top board bottom at z=30 -> z[30,42]
Z_BOTTOM = -T          # translate for bottom board (built 0..T)
Z_TOP = GAP            # translate for top board -> 30..42
Z_POST = -PIN_L        # post built 0..60, seated so mid section fills the gap


def cross_positions():
    """33 standard English peg-solitaire hole centers (7x7 minus 2x2 corners)."""
    pts = []
    for r in range(7):
        for c in range(7):
            in_corner = (c in (0, 1, 5, 6)) and (r in (0, 1, 5, 6))
            if not in_corner:
                pts.append((round((c - 3) * PITCH, 6), round((r - 3) * PITCH, 6)))
    return pts


def make_board():
    """One 180x180x12 cross board: 33 blind peg holes + 4 corner through-bores."""
    vert = cq.Workplane("XY").box(2 * ARM_HALF, BOARD, T, centered=(True, True, False))
    horiz = cq.Workplane("XY").box(BOARD, 2 * ARM_HALF, T, centered=(True, True, False))
    board = vert.union(horiz)

    # bosses filling the four notch corners, anchored on the arms
    for sx in (1, -1):
        for sy in (1, -1):
            boss = (cq.Workplane("XY")
                    .center(sx * POST_XY, sy * POST_XY)
                    .box(BOSS, BOSS, T, centered=(True, True, False)))
            board = board.union(boss)

    # blind peg holes, D12 x 8 deep from the top face (floor at z=4)
    for (x, y) in cross_positions():
        cutter = (cq.Workplane("XY").center(x, y)
                  .circle(HOLE_D / 2).extrude(HOLE_DEPTH)
                  .translate((0, 0, T - HOLE_DEPTH)))
        board = board.cut(cutter)

    # corner bores, D7.85 through the full thickness (pins protrude 3 mm each side)
    for sx in (1, -1):
        for sy in (1, -1):
            bore = (cq.Workplane("XY").center(sx * POST_XY, sy * POST_XY)
                    .circle(BORE_D / 2).extrude(T + 2).translate((0, 0, -1)))
            board = board.cut(bore)

    bb = board.val().BoundingBox()
    assert abs(bb.xlen - BOARD) < 1e-4, bb.xlen
    assert abs(bb.ylen - BOARD) < 1e-4, bb.ylen
    assert abs(bb.zlen - T) < 1e-4, bb.zlen
    return board


def make_post():
    """Plain D10 x 60 post with a stepped D8 x 15 insertion pin at each end."""
    p = cq.Workplane("XY").circle(PIN_D / 2).extrude(PIN_L)                 # bottom pin 0..15
    p = p.faces(">Z").workplane().circle(POST_D / 2).extrude(POST_L - 2 * PIN_L)  # barrel 15..45
    p = p.faces(">Z").workplane().circle(PIN_D / 2).extrude(PIN_L)          # top pin 45..60
    bb = p.val().BoundingBox()
    assert abs(bb.zlen - POST_L) < 1e-4, bb.zlen
    return p


def make_peg():
    """Loose peg, D11.4 x 20."""
    return cq.Workplane("XY").circle(PEG_D / 2).extrude(PEG_H)


PART_DESCRIPTIONS = {
    "board_bottom": "Bottom cross board, 180x180x12, 33 peg holes + 4 corner bores.",
    "board_top": "Top cross board, identical to bottom, stacked 30 mm above it.",
    "post_1": "Corner support post, D10x60 with D8x15 press-fit pins.",
    "post_2": "Corner support post, D10x60 with D8x15 press-fit pins.",
    "post_3": "Corner support post, D10x60 with D8x15 press-fit pins.",
    "post_4": "Corner support post, D10x60 with D8x15 press-fit pins.",
    "peg_floating": "Loose peg suspended on the center axis in the 30 mm gap.",
}


def gen_step():
    asm = cq.Assembly()

    holes = cross_positions()
    assert len(holes) == 33, len(holes)
    center = (0.0, 0.0)

    board = make_board()
    asm.add(board, name="board_bottom", loc=cq.Location(cq.Vector(0, 0, Z_BOTTOM)))
    asm.add(board, name="board_top", loc=cq.Location(cq.Vector(0, 0, Z_TOP)))

    post = make_post()
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (-1, -1), (1, -1)]):
        asm.add(post, name=f"post_{i + 1}",
                loc=cq.Location(cq.Vector(sx * POST_XY, sy * POST_XY, Z_POST)))

    peg = make_peg()

    # Bottom board: seat every hole except the center and one arm-tip.
    # (Two full boards would need 65 pegs for a floating one; we have 64.)
    extra_empty = (0.0, -72.0)
    z_bottom_floor = 0.0 - HOLE_DEPTH        # bottom-board hole floor at z=-8
    n = 0
    for (x, y) in holes:
        if (x, y) in (center, extra_empty):
            continue
        asm.add(peg, name=f"peg_bottom_{n}",
                loc=cq.Location(cq.Vector(x, y, z_bottom_floor)))
        n += 1

    # Top board: seat every hole except the center.
    z_top_floor = (Z_TOP + T) - HOLE_DEPTH   # top-board hole floor at z=34
    m = 0
    for (x, y) in holes:
        if (x, y) == center:
            continue
        asm.add(peg, name=f"peg_top_{m}",
                loc=cq.Location(cq.Vector(x, y, z_top_floor)))
        m += 1

    # Floating peg: on the bottom-center axis, centered in the gap (5 mm air each side).
    z_float = (GAP - PEG_H) / 2.0            # -> 5 mm, peg spans z[5,25]
    asm.add(peg, name="peg_floating", loc=cq.Location(cq.Vector(0, 0, z_float)))

    total = 4 + n + m + 1
    assert total == 4 + 64, total          # 4 posts + 64 pegs
    return asm
