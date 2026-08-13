"""Hard asserts on every dimension brief.json states or fixes."""
from __future__ import annotations

from params import Params


def validate_params(p: Params) -> None:
    # plinth_axle
    assert p.drum_diameter_mm == 190.0
    assert p.drum_height_mm == 22.0
    assert p.axle_post_height_mm == 40.0
    assert abs(p.axle_post_diameter_mm - 12.2) < 1e-9, p.axle_post_diameter_mm
    assert p.center_bore_mm == 13.0
    assert p.socket_depth_mm == 10.0
    assert p.socket_count == 8
    assert p.socket_ring_radius_mm == 75.0
    assert p.socket_floor_remaining_material_mm == 12.0
    assert p.index_groove_count == 8
    assert p.index_groove_depth_mm == 1.0
    assert p.constellation_relief_mm == 0.8
    # overall plinth height == drum + post, matching brief bbox_mm z=62
    assert p.drum_height_mm + p.axle_post_height_mm == 62.0

    # tier discs
    assert p.disc_diameter_mm == 190.0
    assert p.disc_thickness_mm == 10.0
    assert p.window_diameter_mm == 9.0
    assert p.window_count == 3
    assert p.window_ring_radius_mm == 75.0
    assert p.grip_tab_width_mm == 18.0
    assert p.grip_tab_projection_mm == 16.0
    assert p.witness_notch_depth_mm == 1.0
    # bbox_mm X = disc diameter + one-sided tab projection == 206
    assert p.disc_diameter_mm + p.grip_tab_projection_mm == 206.0
    for key in p.tier_order:
        assert len(p.window_indices[key]) == p.window_count
        assert all(0 <= i < p.ring_count for i in p.window_indices[key])
    assert len({tuple(sorted(v)) for v in p.window_indices.values()}) == 3, \
        "each disc must have a DISTINCT window pattern"

    # marker pegs
    assert p.peg_base_mm == 11.0
    assert p.peg_height_mm == 20.0
    assert p.peg_seat_clearance_mm == 1.5
    assert p.socket_diameter_mm == 14.0
    assert p.peg_qty_per_family == 4
    assert set(p.peg_sides.values()) == {3, 4, 5, 6}
    # peg proud height once seated (brief: stands 10mm proud of the rim)
    assert p.peg_height_mm - p.socket_depth_mm == 10.0

    # probe pin
    assert p.probe_shaft_diameter_mm == 6.0
    assert p.probe_shaft_length_mm == 40.0
    assert p.probe_head_diameter_mm == 16.0
    assert p.probe_head_thickness_mm == 6.0
    assert p.probe_total_length_mm == 46.0
    # calibration: 3 disc thicknesses + one socket depth == shaft length
    assert 3 * p.disc_thickness_mm + p.socket_depth_mm == p.probe_shaft_length_mm


def functional_warnings(p: Params) -> list[dict]:
    """Soft assembly-feasibility checks -- empty when the design is sound."""
    warnings: list[dict] = []
    if p.axle_post_diameter_mm >= p.center_bore_mm:
        warnings.append({
            "severity": "warning",
            "code": "functional",
            "message": "axle post does not clear the disc center bore",
        })
    if p.peg_base_mm >= p.socket_diameter_mm:
        warnings.append({
            "severity": "warning",
            "code": "functional",
            "message": "marker peg base does not clear the plinth socket",
        })
    return warnings
