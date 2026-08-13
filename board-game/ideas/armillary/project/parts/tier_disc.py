"""tier_disc_a/b/c -- 190mm dia x 10mm disc, 13mm center bore, 3 windows on
the shared ring, a grip tab told apart by shape, one witness notch on the
rim. Prints flat, thickest face down.
"""
from __future__ import annotations

import cadquery as cq

from features.ring import ring_xy


def _build_tab(p, shape_name: str) -> cq.Workplane:
    r = p.disc_diameter_mm / 2.0
    # start the base WELL INSIDE the disc's circular boundary -- a straight
    # base edge at exactly x=r only touches the round disc at one point
    # (y=0), which fuses into a sliver / disconnected solid, not a union.
    base = r - 10.0
    w2 = p.grip_tab_width_mm / 2.0
    tip = r + p.grip_tab_projection_mm

    if shape_name == "rounded_paddle":
        straight_x = tip - w2
        profile = (
            cq.Workplane("XY")
            .moveTo(base, -w2)
            .lineTo(straight_x, -w2)
            .threePointArc((tip, 0), (straight_x, w2))
            .lineTo(base, w2)
            .close()
        )
    elif shape_name == "pointed_triangular_fin":
        profile = (
            cq.Workplane("XY")
            .moveTo(base, -w2)
            .lineTo(base, w2)
            .lineTo(tip, 0)
            .close()
        )
    elif shape_name == "notched_double_prong":
        pinch_x = r + (tip - r) * 0.35
        profile = (
            cq.Workplane("XY")
            .moveTo(base, -w2)
            .lineTo(tip, -w2)
            .lineTo(tip, -w2 * 0.25)
            .lineTo(pinch_x, 0)
            .lineTo(tip, w2 * 0.25)
            .lineTo(tip, w2)
            .lineTo(base, w2)
            .close()
        )
    else:
        raise ValueError(f"unknown grip_tab_shape {shape_name!r}")

    return profile.extrude(p.disc_thickness_mm)


def build(p, key: str) -> cq.Workplane:
    disc = (
        cq.Workplane("XY")
        .circle(p.disc_diameter_mm / 2.0)
        .extrude(p.disc_thickness_mm)
    )
    disc = disc.faces(">Z").workplane().hole(p.center_bore_mm)

    win_angles = [p.ring_angles_deg[i] for i in p.window_indices[key]]
    for x, y in ring_xy(p.window_ring_radius_mm, win_angles):
        cutter = (
            cq.Workplane("XY")
            .cylinder(p.disc_thickness_mm * 2, p.window_diameter_mm / 2.0)
            .translate((x, y, p.disc_thickness_mm / 2.0))
        )
        disc = disc.cut(cutter)

    disc = disc.union(_build_tab(p, p.grip_tab_shapes[key]))

    # witness notch: a small dimple on the rim, opposite the grip tab
    notch_cutter = (
        cq.Workplane("XY")
        .box(p.witness_notch_depth_mm * 2, 4.0, p.disc_thickness_mm)
        .translate((-p.disc_diameter_mm / 2.0, 0, p.disc_thickness_mm / 2.0))
    )
    disc = disc.cut(notch_cutter)

    return disc
