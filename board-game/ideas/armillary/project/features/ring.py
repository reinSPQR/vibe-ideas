"""The one angular position list, projected to whatever radius a feature needs.

`params.Params.ring_angles_deg` is generated exactly once. Every caller here
(plinth sockets, plinth index grooves, constellation dots, every disc's
window ring) reuses that same angle list -- never regenerates its own.
"""
from __future__ import annotations

import math


def ring_xy(radius: float, angles_deg: list[float]) -> list[tuple[float, float]]:
    """Project a shared angle list onto a circle of the given radius."""
    return [
        (radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)))
        for a in angles_deg
    ]
