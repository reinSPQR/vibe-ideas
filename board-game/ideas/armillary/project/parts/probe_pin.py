"""probe_pin -- 6mm dia x 40mm shaft under a 16mm dia x 6mm flared head.
The shared verification tool. Prints head down.
"""
from __future__ import annotations

import cadquery as cq


def build(p) -> cq.Workplane:
    shaft = (
        cq.Workplane("XY")
        .circle(p.probe_shaft_diameter_mm / 2.0)
        .extrude(p.probe_shaft_length_mm)
    )
    head = (
        cq.Workplane("XY")
        .workplane(offset=p.probe_shaft_length_mm)
        .circle(p.probe_head_diameter_mm / 2.0)
        .extrude(p.probe_head_thickness_mm)
    )
    body = shaft.union(head)
    # soften the head's top rim only -- an easy, unambiguous edge to grab
    body = body.faces(">Z").edges().fillet(1.0)
    return body
