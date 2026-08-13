"""Armillary -- draft entrypoint. See board-game/ideas/armillary/brief.json."""
from __future__ import annotations

from params import Params
from validation import functional_warnings, validate_params
from assemblies.product import make_assembly

PART_DESCRIPTIONS = {
    "plinth_axle": "Fixed base: 190mm drum + 40mm axle post, 8 sockets, 8 index grooves.",
    "tier_disc_a": "Tier 1 disc, rounded-paddle grip tab, windows at ring indices 0/3/6.",
    "tier_disc_b": "Tier 2 disc, pointed triangular-fin grip tab, windows at ring indices 1/4/6.",
    "tier_disc_c": "Tier 3 disc, notched double-prong grip tab, windows at ring indices 2/5/7.",
    "probe_pin": "Shared verification tool: 6mm x 40mm shaft under a 16mm x 6mm flared head.",
}


def gen_step():
    p = Params()
    validate_params(p)
    return {"shape": make_assembly(p), "warnings": functional_warnings(p)}
