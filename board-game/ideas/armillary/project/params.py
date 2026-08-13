"""All dimensions for Armillary, sourced from brief.json.

Every mating pair derives from ONE nominal + ONE clearance (see the
`_seat*` and `axle_post_diameter_mm` derivations below) so the two halves
of a mate cannot drift apart across an edit.
"""
from __future__ import annotations

from cadlib.fits import peg_for


class Params:
    def __init__(self) -> None:
        # ---- shared 8-position ring (sockets / grooves / disc windows) ----
        # ONE angle list, reused (at different radii) by plinth sockets,
        # plinth index grooves, the constellation dots, and every disc's
        # window ring. Never restate these angles.
        self.ring_count = 8
        self.ring_angles_deg = [i * 360.0 / self.ring_count for i in range(self.ring_count)]
        self.socket_ring_radius_mm = 75.0
        self.window_ring_radius_mm = 75.0  # same physical ring as the sockets

        # ---- plinth_axle ----
        self.drum_diameter_mm = 190.0
        self.drum_height_mm = 22.0
        self.axle_post_height_mm = 40.0

        # disc center bore is the female; axle post is the male peg derived
        # from it at a "free" (0.40mm/side) spin fit -> 13 - 0.8 = 12.2mm
        self.center_bore_mm = 13.0
        self.axle_post_diameter_mm = peg_for(self.center_bore_mm, "free")

        self.socket_depth_mm = 10.0
        self.socket_count = 8
        self.socket_floor_remaining_material_mm = self.drum_height_mm - self.socket_depth_mm

        self.index_groove_count = 8
        self.index_groove_depth_mm = 1.0
        self.index_groove_width_mm = 3.0

        self.constellation_relief_mm = 0.8
        self.constellation_dot_diameter_mm = 6.0

        # ---- tier discs ----
        self.disc_diameter_mm = 190.0
        self.disc_thickness_mm = 10.0
        self.window_diameter_mm = 9.0
        self.window_count = 3
        self.grip_tab_width_mm = 18.0
        self.grip_tab_projection_mm = 16.0
        self.witness_notch_depth_mm = 1.0
        self.tier_count = 3

        self.tier_order = ["tier_disc_a", "tier_disc_b", "tier_disc_c"]
        self.grip_tab_shapes = {
            "tier_disc_a": "rounded_paddle",
            "tier_disc_b": "pointed_triangular_fin",
            "tier_disc_c": "notched_double_prong",
        }
        # a different fixed 3-of-8 window pattern per disc (indices into
        # ring_angles_deg) -- this pattern IS the game mechanism
        self.window_indices = {
            "tier_disc_a": [0, 3, 6],
            "tier_disc_b": [1, 4, 6],
            "tier_disc_c": [2, 5, 7],
        }
        # setup rotation, counted in grooves (45deg each) -- also used to
        # spread the three distinct grip tabs around the assembled tower
        self.starting_index_offset_grooves = {
            "tier_disc_a": 2,
            "tier_disc_b": 4,
            "tier_disc_c": 6,
        }

        # ---- marker pegs (4 families x 4 each) ----
        self.peg_base_mm = 11.0          # the piece owns this dimension
        self.peg_height_mm = 20.0
        self.peg_seat_clearance_mm = 1.5  # per side, from brief interfaces
        # the plinth socket is the female, derived from the peg (the male)
        # plus the one stated clearance -- never sized independently
        self.socket_diameter_mm = self.peg_base_mm + 2 * self.peg_seat_clearance_mm
        self.peg_qty_per_family = 4
        self.peg_sides = {
            "marker_peg_tri": 3,
            "marker_peg_square": 4,
            "marker_peg_penta": 5,
            "marker_peg_hex": 6,
        }

        # ---- probe pin ----
        self.probe_shaft_diameter_mm = 6.0
        self.probe_shaft_length_mm = 40.0
        self.probe_head_diameter_mm = 16.0
        self.probe_head_thickness_mm = 6.0
        self.probe_total_length_mm = self.probe_shaft_length_mm + self.probe_head_thickness_mm
