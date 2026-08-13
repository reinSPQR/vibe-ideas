"""Places every physical part as a separately named cq.Assembly child.

Layout for the hero render: the plinth + 3 stacked discs form the tower
(each disc rotated to its brief-stated setup offset, PLUS one shared display
offset that turns the tabs to face the review tool's fixed hero camera --
see `_DISC_DISPLAY_DEG`); the 16 marker pegs and the probe pin sit in front
of the tower, flanking the camera direction on either side, since a peg
seated under a closed disc stack is hidden by design (that is the game's
hidden-information mechanic) and would only read as a collision here.
"""
from __future__ import annotations

import math

import cadquery as cq

from blocks import add_piece_family
from parts import plinth_axle, tier_disc, marker_peg, probe_pin

# cadcode/scripts/review's single-iso hero cover is rendered at a FIXED
# azim=-35, elev=10 (see review/cli.py _COVER_VIEWS) -- i.e. the camera looks
# toward the world origin from world-space azimuth ~325deg. Nothing here can
# change that camera; instead every placement below is chosen relative to
# this fixed direction so the defining features end up facing it.
_CAMERA_AZIMUTH_DEG = -35.0

# Extra Z rotation baked into every disc placement (on top of the brief's
# own groove-counted setup offset) so the three grip tabs -- the tiers' one
# visual differentiator -- land near the camera instead of on the far side.
# Chosen so tier_disc_b's fin sits dead-center on camera and the other two
# flank it at +-90deg (still visible at a glancing angle).
_DISC_DISPLAY_DEG = 145.0


def _dir_vec(angle_deg: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return (math.cos(a), math.sin(a))


def make_assembly(p) -> cq.Assembly:
    asm = cq.Assembly(name="armillary")
    display = cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), _DISC_DISPLAY_DEG)

    asm.add(plinth_axle.build(p), name="plinth_axle",
            loc=display * cq.Location(cq.Vector(0, 0, 0)))

    z = p.drum_height_mm
    for key in p.tier_order:
        shape = tier_disc.build(p, key)
        angle = p.starting_index_offset_grooves[key] * (360.0 / p.ring_count)
        loc = display * cq.Location(cq.Vector(0, 0, z), cq.Vector(0, 0, 1), angle)
        asm.add(shape, name=key, loc=loc)
        z += p.disc_thickness_mm

    # --- marker pegs: 4 families x 4, fanned out from the tower toward the
    # camera, offset to one side of it so they read beside the tower rather
    # than behind or directly in front of it ---
    gap = 8.0
    radial_pitch = p.peg_base_mm + 5.0
    tangential_pitch = p.peg_base_mm + 5.0
    peg_az = _CAMERA_AZIMUTH_DEG - 45.0
    u = _dir_vec(peg_az)            # radially outward from the tower
    v = (-u[1], u[0])               # tangential (sideways spread)
    origin_r = p.drum_diameter_mm / 2.0 + gap
    families = list(p.peg_sides.keys())
    fam_half = (len(families) - 1) * tangential_pitch / 2.0
    for fam_idx, name in enumerate(families):
        sides = p.peg_sides[name]
        shape = marker_peg.build(p, sides)
        t = fam_idx * tangential_pitch - fam_half
        positions = [
            (
                (origin_r + col * radial_pitch) * u[0] + t * v[0],
                (origin_r + col * radial_pitch) * u[1] + t * v[1],
                0.0,
            )
            for col in range(p.peg_qty_per_family)
        ]
        add_piece_family(asm, shape, positions, name)

    # --- probe pin: laid flat, pointing straight out from the tower on the
    # other side of the camera direction from the peg fan ---
    pin_az = _CAMERA_AZIMUTH_DEG + 45.0
    pu = _dir_vec(pin_az)
    pin_shape = (
        probe_pin.build(p)
        .rotate((0, 0, 0), (0, 1, 0), 90)   # lay flat, shaft along local +X
        .rotate((0, 0, 0), (0, 0, 1), pin_az)  # point it along pu
    )
    pin_r = p.drum_diameter_mm / 2.0 + gap
    asm.add(pin_shape, name="probe_pin",
            loc=cq.Location(cq.Vector(pin_r * pu[0], pin_r * pu[1],
                                       p.probe_head_diameter_mm / 2.0)))

    return asm
