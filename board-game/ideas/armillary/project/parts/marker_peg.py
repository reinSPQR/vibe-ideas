"""marker_peg_tri/square/penta/hex -- 11mm-across polygonal prism, 20mm
tall, domed top. Told apart purely by cross-section. Prints base down.
"""
from __future__ import annotations

import cadquery as cq


def build(p, sides: int) -> cq.Workplane:
    prism = (
        cq.Workplane("XY")
        .polygon(sides, p.peg_base_mm)
        .extrude(p.peg_height_mm)
    )
    dome_radius = p.peg_base_mm / 2.0 * 0.9
    dome = (
        cq.Workplane("XY")
        .sphere(dome_radius)
        .translate((0, 0, p.peg_height_mm))
    )
    return prism.union(dome)
