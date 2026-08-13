"""plinth_axle -- 190mm dia x 22mm drum + 40mm axle post, 8 sockets, 8 index
grooves, constellation relief dots. Prints drum-face down, sockets open up.
"""
from __future__ import annotations

import cadquery as cq

from blocks import cut_wells
from features.ring import ring_xy


def build(p) -> cq.Workplane:
    drum = (
        cq.Workplane("XY")
        .circle(p.drum_diameter_mm / 2.0)
        .extrude(p.drum_height_mm)
    )
    post = (
        cq.Workplane("XY")
        .workplane(offset=p.drum_height_mm)
        .circle(p.axle_post_diameter_mm / 2.0)
        .extrude(p.axle_post_height_mm)
    )
    body = drum.union(post)

    # 8 sockets on the shared ring -- no thumb scallop: at 75mm radius / 14mm
    # dia the sockets sit close enough together that a scallop would breach
    # the neighbouring socket wall.
    socket_xy = ring_xy(p.socket_ring_radius_mm, p.ring_angles_deg)
    socket_positions = [(x, y, p.drum_height_mm) for x, y in socket_xy]
    body = cut_wells(
        body, socket_positions, p.socket_diameter_mm, p.socket_depth_mm,
        top_z=p.drum_height_mm, notch=False,
    )

    # 8 index grooves at the SAME angles, cut into the rim, full drum height
    groove_xy = ring_xy(p.drum_diameter_mm / 2.0, p.ring_angles_deg)
    for i, (x, y) in enumerate(groove_xy):
        angle = p.ring_angles_deg[i]
        cutter = (
            cq.Workplane("XY")
            .box(p.index_groove_depth_mm * 2, p.index_groove_width_mm, p.drum_height_mm)
            .translate((p.drum_diameter_mm / 2.0, 0, p.drum_height_mm / 2.0))
            .rotate((0, 0, 0), (0, 0, 1), angle)
        )
        body = body.cut(cutter)

    # constellation relief dots, offset half a step from the sockets -- a
    # transform of the SAME shared angle list, not a new one
    half_step = 360.0 / p.ring_count / 2.0
    dot_angles = [a + half_step for a in p.ring_angles_deg]
    dot_xy = ring_xy(p.socket_ring_radius_mm, dot_angles)
    for x, y in dot_xy:
        dot = (
            cq.Workplane("XY")
            .cylinder(p.constellation_relief_mm, p.constellation_dot_diameter_mm / 2.0)
            .translate((x, y, p.drum_height_mm + p.constellation_relief_mm / 2.0))
        )
        body = body.union(dot)

    return body
