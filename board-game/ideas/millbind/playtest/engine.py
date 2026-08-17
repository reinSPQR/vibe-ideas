"""engine.py — millbind, an executable model of idea.json. Not a game to play."""
from __future__ import annotations

import random  # only used via the rng argument playtest.py passes in


class Undefined(Exception):
    """The rules do not say."""


SLUG = "millbind"
PLAYERS = (2, 4)
MAX_TURNS = 300
MOVE_KINDS = ("setup_mill", "setup_crank", "power", "place", "shift", "pass")
HIDDEN_INFO = False   # the whole yard, the supply pile and every score are open
ASSUMPTIONS = []       # no reading found where BOTH branches let play continue,
CHOICES = {}            # before or after the rework; see notes.md


# ---------------------------------------------------------------------------
# Board geometry: 37 pins on a triangular lattice — centre, ring of 6, ring
# of 12, ring of 18 — addressed with cube/axial hex coordinates (q, r),
# s = -q - r, ring = max(|q|, |r|, |s|). The six standard axial neighbour
# offsets are exactly the six nearest-neighbour directions of a triangular
# lattice at unit spacing, which is what the 30mm pin spacing is, so "hex
# distance 1" and "physically 30mm apart, meshable if teeth match" are the
# same relation. Only the outer ring (ring == 3, 18 pins) is a yard pin.
# ---------------------------------------------------------------------------

def _gen_pins():
    pins = []
    for q in range(-3, 4):
        for r in range(-3, 4):
            s = -q - r
            if max(abs(q), abs(r), abs(s)) <= 3:
                pins.append((q, r))
    return pins


def _ring(p):
    q, r = p
    s = -q - r
    return max(abs(q), abs(r), abs(s))


PIN_LIST = _gen_pins()
assert len(PIN_LIST) == 37, f"lattice should hold 37 pins, built {len(PIN_LIST)}"
YARD_PINS = [p for p in PIN_LIST if _ring(p) == 3]
INNER_PINS = [p for p in PIN_LIST if _ring(p) < 3]
assert len(YARD_PINS) == 18 and len(INNER_PINS) == 19

_PIN_SET = set(PIN_LIST)
_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
NEIGHBORS = {}
for _p in PIN_LIST:
    _q, _r = _p
    NEIGHBORS[_p] = [c for c in ((_q + dq, _r + dr) for dq, dr in _DIRS) if c in _PIN_SET]

EDGES = []
_seen = set()
for _p, _nbrs in NEIGHBORS.items():
    for _q in _nbrs:
        e = (_p, _q) if _p < _q else (_q, _p)
        if e not in _seen:
            _seen.add(e)
            EDGES.append(e)


# ---------------------------------------------------------------------------
# MESHING (rules:turn[0]) and TEST FOR A BIND (rules:turn[5]): the bind test
# is a whole-graph odd-cycle check, subject to the two tooth tiers. gear_low
# meshes only with gear_low, gear_high only with gear_high; gear_tandem, a
# millstone and the crank_gear are full-height and mesh with anything on a
# neighbouring pin. "Neighbouring" is the lattice adjacency above.
#
# rules:turn[5] now scopes the test to every arrival on a pin — PLACE, SHIFT
# AND the crank's own move in POWER (rules:turn[1]) — so this section is
# used from three call sites: PLACE/SHIFT test-then-revert in apply_move,
# and POWER filters candidate pins in legal_moves with the crank's old pin
# hypothetically empty, below.
# ---------------------------------------------------------------------------

def _tier(piece):
    t = piece["type"]
    if t == "gear_low":
        return "low"
    if t == "gear_high":
        return "high"
    return "full"   # gear_tandem, mill, crank


def _meshes(a, b):
    ta, tb = _tier(a), _tier(b)
    return ta == "full" or tb == "full" or ta == tb


def _build_adj(pins):
    adj = {p: [] for p in PIN_LIST if pins[p] is not None}
    for p, q in EDGES:
        pp, pq = pins[p], pins[q]
        if pp is not None and pq is not None and _meshes(pp, pq):
            adj[p].append(q)
            adj[q].append(p)
    return adj


def _analyze_graph(adj):
    """2-colour every component; a colour clash anywhere is an odd cycle —
    the whole yard is bound, exactly the physical fact the rules describe.
    Returns (colour, component_id, bound)."""
    color, comp = {}, {}
    bound = False
    cid = 0
    for start in adj:
        if start in color:
            continue
        color[start] = 0
        comp[start] = cid
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in color:
                    color[v] = color[u] ^ 1
                    comp[v] = cid
                    stack.append(v)
                elif color[v] == color[u]:
                    bound = True
        cid += 1
    return color, comp, bound


def _is_bound_state(state) -> bool:
    _, _, bound = _analyze_graph(_build_adj(state["pins"]))
    return bound


def _would_bind(pins, overrides):
    """Hypothetical bind test: apply `overrides` to a COPY of `pins` (pin ->
    None or a piece dict) and report whether that trial layout is bound,
    without mutating `pins`. Used by POWER (rules:turn[1]/[5]) to test a
    candidate crank pin before it is ever actually stood there."""
    trial = dict(pins)
    trial.update(overrides)
    _, _, bound = _analyze_graph(_build_adj(trial))
    return bound


# ---------------------------------------------------------------------------
# Setup (rules:setup[3..4]). rules:setup[4] now bind-tests every setup
# placement too, but also states it "cannot fail here" and gives the reason:
# the 18 yard pins form a single 18-cycle (verified in _gen_pins/NEIGHBORS
# above and independently in review_playtest.md's own probe), and only
# full-height millstones and the crank stand on yard pins during setup (no
# supply gear is placed yet), so every possible setup mesh graph is a
# subgraph of that one bipartite cycle and can never contain an odd loop.
# That is a proof, not a hope, so setup does not test-then-revert like
# PLACE/SHIFT — it asserts the geometry instead, which is the honest way to
# encode "provably unreachable" rather than writing dead fallback code that
# a thousand games could never exercise.
# ---------------------------------------------------------------------------

def new_game(n_players, rng):
    if n_players < PLAYERS[0] or n_players > PLAYERS[1]:
        raise ValueError(f"millbind seats {PLAYERS[0]}-{PLAYERS[1]}, not {n_players}")
    return {
        "n_players": n_players,
        "pins": {p: None for p in PIN_LIST},
        "supply": {"gear_low": 14, "gear_high": 7, "gear_tandem": 3},
        "pellets": 28,
        "spindles": [0] * n_players,
        "start_player": 0,          # "choose a first player any way you like"
        "phase": "setup_mill",
        "setup_index": 0,
        "crank_pin": None,
        "mill_pin": [None] * n_players,
        "action_order": [],
        "action_index": 0,
        "placed_this_round": False,
        "last_grind_cw": [],
        "round": 0,
        "game_over": False,
    }


def player_to_move(state):
    phase = state["phase"]
    if phase == "setup_mill":
        return state["setup_index"]
    if phase in ("setup_crank", "power"):
        return state["start_player"]
    if phase == "actions":
        return state["action_order"][state["action_index"]]
    raise RuntimeError(f"no player to move in phase {phase!r}")


# ---------------------------------------------------------------------------
# legal_moves — pure, no mutation
# ---------------------------------------------------------------------------

def legal_moves(state):
    phase = state["phase"]
    pins = state["pins"]

    if phase == "setup_mill":
        return [("setup_mill", p) for p in YARD_PINS if pins[p] is None]

    if phase == "setup_crank":
        return [("setup_crank", p) for p in YARD_PINS if pins[p] is None]

    if phase == "power":
        # rules:turn[1] POWER / rules:turn[5] TEST FOR A BIND (rescoped to
        # cover the crank's own move). A candidate pin is a legal home for
        # the crank this round only if the crank does not bind there,
        # tested with the crank's OLD pin hypothetically empty (the crank
        # is not on two pins at once during the test). Retries are free and
        # unlimited and POWER is not one of the three actions, so a
        # binding candidate simply is not offered rather than being
        # attempted then reverted. Staying on the crank's own pin is always
        # legal per the text, and is never itself a bind risk: the yard was
        # proven not bound at the end of the previous round (THE GRIND,
        # rules:turn[7], only completes from an unbound yard) and staying
        # changes nothing about the mesh graph.
        old_pin = state["crank_pin"]
        moves = [("power", old_pin)]
        for p in YARD_PINS:
            if p != old_pin and pins[p] is None:
                if not _would_bind(pins, {old_pin: None, p: {"type": "crank"}}):
                    moves.append(("power", p))
        return moves

    if phase == "actions":
        seat = state["action_order"][state["action_index"]]
        moves = [("pass",)]
        for gtype, cnt in state["supply"].items():
            if cnt > 0:
                for p in PIN_LIST:
                    if pins[p] is None:
                        moves.append(("place", p, gtype))
        own_pin = state["mill_pin"][seat]
        for p in YARD_PINS:
            if pins[p] is None and p != own_pin:
                moves.append(("shift", p))
        return moves

    return []   # phase == "over"


# ---------------------------------------------------------------------------
# apply_move — may mutate, must return the state
# ---------------------------------------------------------------------------

def _advance_action(state):
    state["action_index"] += 1
    if state["action_index"] >= state["n_players"]:
        _process_grind(state)


def apply_move(state, move, rng):
    kind = move[0]

    if kind == "setup_mill":
        seat = state["setup_index"]
        pin = move[1]
        state["pins"][pin] = {"type": "mill", "owner": seat}
        state["mill_pin"][seat] = pin
        assert not _is_bound_state(state), (
            "rules:setup[4]: setup produced a bound yard, which the "
            "eighteen-pin yard ring should make geometrically impossible"
        )
        state["setup_index"] += 1
        if state["setup_index"] >= state["n_players"]:
            state["phase"] = "setup_crank"
        return state

    if kind == "setup_crank":
        pin = move[1]
        state["pins"][pin] = {"type": "crank"}
        state["crank_pin"] = pin
        assert not _is_bound_state(state), (
            "rules:setup[4]: setup produced a bound yard, which the "
            "eighteen-pin yard ring should make geometrically impossible"
        )
        state["phase"] = "power"
        return state

    if kind == "power":
        # legal_moves already bind-tested every candidate (rules:turn[1]/
        # [5]); a move reaching here is guaranteed non-binding, so it is
        # simply applied, with no test-then-revert as PLACE/SHIFT use.
        target = move[1]
        if target != state["crank_pin"]:
            state["pins"][state["crank_pin"]] = None
            state["pins"][target] = {"type": "crank"}
            state["crank_pin"] = target
        n = state["n_players"]
        sp = state["start_player"]
        state["action_order"] = [(sp + i) % n for i in range(n)]
        state["action_index"] = 0
        state["placed_this_round"] = False
        state["phase"] = "actions"
        return state

    if kind == "place":
        _, pin, gtype = move
        state["pins"][pin] = {"type": gtype}
        state["supply"][gtype] -= 1
        # rules:turn[5] TEST FOR A BIND
        if _is_bound_state(state):
            state["pins"][pin] = None
            state["supply"][gtype] += 1
        else:
            state["placed_this_round"] = True
        _advance_action(state)
        return state

    if kind == "shift":
        seat = state["action_order"][state["action_index"]]
        _, new_pin = move
        old_pin = state["mill_pin"][seat]
        piece = state["pins"][old_pin]
        state["pins"][old_pin] = None
        state["pins"][new_pin] = piece
        state["mill_pin"][seat] = new_pin
        # rules:turn[5] TEST FOR A BIND
        if _is_bound_state(state):
            state["pins"][new_pin] = None
            state["pins"][old_pin] = piece
            state["mill_pin"][seat] = old_pin
        _advance_action(state)
        return state

    if kind == "pass":
        _advance_action(state)
        return state

    raise ValueError(f"millbind engine does not know move kind {kind!r}")


# ---------------------------------------------------------------------------
# THE GRIND (rules:turn[7]), A SHORT GRANARY (rules:turn[8]) and DIRECTION
# (rules:turn[9])
# ---------------------------------------------------------------------------

def _process_grind(state):
    adj = _build_adj(state["pins"])
    color, comp, bound = _analyze_graph(adj)

    if bound:
        # rules:turn[7] THE GRIND now asserts the crank always turns here,
        # because every move that could bind the yard is tested before it
        # takes effect: POWER (rules:turn[1]) only ever offers non-binding
        # candidate pins (see legal_moves), and every PLACE/SHIFT
        # (rules:turn[5]) is tested-then-reverted in apply_move. So a bound
        # yard reaching THE GRIND means one of those guarantees failed to
        # hold in THIS engine — a defect in the code, not the rules gap the
        # rework closed. rules:turn[7]'s own recovery clause ("undo this
        # round's moves ... until it turns") exists for a human table that
        # skipped a test, which cannot happen here, so this is an assertion
        # rather than an Undefined.
        raise AssertionError(
            "rules:turn[7]: THE GRIND reached a bound yard although every "
            "move this round was bind-tested before taking effect; this "
            "indicates an engine bug, not a remaining rules gap."
        )

    crank_pin = state["crank_pin"]
    crank_color = color.get(crank_pin)
    crank_comp = comp.get(crank_pin)

    cw_seats = []
    for seat in range(state["n_players"]):
        mp = state["mill_pin"][seat]
        if mp is not None and comp.get(mp) == crank_comp and color.get(mp) == crank_color:
            cw_seats.append(seat)

    # rules:turn[8] A SHORT GRANARY: hand pellets out one at a time,
    # beginning with the start player and going clockwise, to each owner
    # still owed something, going round again if anyone is still owed,
    # until every debt is paid or the bin is empty. A lone mill owed 2
    # pellets with 1 left in the bin scores 1, not 0 and not 2. Any debt
    # the empty bin cannot cover is never paid.
    reward = 2 if len(cw_seats) == 1 else 1
    debts = {seat: reward for seat in cw_seats}
    cw_set = set(cw_seats)
    payout_order = [s for s in state["action_order"] if s in cw_set]
    pellets = state["pellets"]
    while pellets > 0 and any(debts[s] > 0 for s in payout_order):
        for seat in payout_order:
            if pellets == 0:
                break
            if debts[seat] > 0:
                debts[seat] -= 1
                pellets -= 1
                state["spindles"][seat] += 1
    state["pellets"] = pellets
    state["last_grind_cw"] = list(cw_seats)

    supply_empty = all(v == 0 for v in state["supply"].values())
    # rules:end[0] / rules:end[1] — end[1] now explicitly covers a grind
    # that ran the bin dry part-way through under A SHORT GRANARY as well
    # as one that exhausted it exactly; both are just state["pellets"] == 0.
    ended = supply_empty or (not state["placed_this_round"]) or state["pellets"] == 0
    state["round"] += 1

    if ended:
        state["game_over"] = True
        state["phase"] = "over"
    else:
        state["start_player"] = (state["start_player"] + 1) % state["n_players"]
        state["phase"] = "power"


# ---------------------------------------------------------------------------
# Termination, score, win (rules:win)
# ---------------------------------------------------------------------------

def is_over(state):
    return bool(state["game_over"])


def scores(state):
    return [float(v) for v in state["spindles"]]


def winners(state):
    spindles = state["spindles"]
    top = max(spindles)
    tied = [i for i, v in enumerate(spindles) if v == top]
    if len(tied) == 1:
        return tied
    cw = set(state.get("last_grind_cw", []))
    tied_cw = [i for i in tied if i in cw]
    if len(tied_cw) == 1:
        return tied_cw
    return tied


# ---------------------------------------------------------------------------
# observation — HIDDEN_INFO is False, so every seat is shown the same board;
# this exists for legibility, not concealment. A raw dump of `state` uses
# variable names chosen for the engine's convenience (`crank_pin` one
# coordinate beside `mill_pin` a per-seat list; a 37-entry `pins` dict that
# is 34 nulls; no statement anywhere of which pins neighbour which, though
# rules:turn[0] MESHING and the whole bind test are written entirely in
# those terms; tooth height left to be inferred from a piece-type string).
# `observation` translates that into idea.json's own vocabulary for a reader
# who has the rulebook and not the code. See notes.md for the reasoning.
# ---------------------------------------------------------------------------

def _pid(p):
    # str() of a (q, r) tuple is "(-1, -2)" — exactly the substring that
    # appears inside every move tuple, e.g. ("place", (-1, -2), "gear_low"),
    # so a pin id here can be matched by eye against the LEGAL MOVES list
    # rather than converted between two different coordinate spellings.
    return str(p)


def observation(state, seat):
    pieces = {}
    for p, piece in state["pins"].items():
        if piece is None:
            continue
        entry = {"piece": piece["type"], "mesh_height": _tier(piece)}
        if piece["type"] == "mill":
            entry["owner"] = piece["owner"]
        pieces[_pid(p)] = entry

    seats = []
    for s in range(state["n_players"]):
        mp = state["mill_pin"][s]
        seats.append({
            "seat": s,
            "mill_pin": _pid(mp) if mp is not None else None,
            "pellets": state["spindles"][s],
        })

    to_move = None if state["game_over"] else player_to_move(state)
    crank_pin = state["crank_pin"]

    return {
        "phase": state["phase"],
        "round": state["round"],
        "to_move": to_move,
        "start_player": state["start_player"],
        "game_over": state["game_over"],
        "crank_pin": _pid(crank_pin) if crank_pin is not None else None,
        "supply": dict(state["supply"]),
        "granary_pellets_remaining": state["pellets"],
        "gear_placed_this_round": state["placed_this_round"],
        "last_grind_clockwise_seats": list(state["last_grind_cw"]),
        "you": seats[seat],
        "seats": seats,
        "board": {
            # rules:setup[0]: the only pins a millstone or the crank may
            # ever stand on. Listed even empty, because SHIFT/POWER offer
            # any empty one of these as a destination.
            "yard_pins": [_pid(p) for p in YARD_PINS],
            "inner_pins": [_pid(p) for p in INNER_PINS],
            # rules:turn[0] MESHING: two pieces on neighbouring pins mesh
            # (subject to mesh_height below); pins that are not neighbours
            # never mesh. This is the fact the whole bind test runs on, and
            # nothing else in the state says which pins these are — a
            # player at the table reads it off the board by eye.
            "edges": [[_pid(a), _pid(b)] for a, b in EDGES],
            # Only occupied pins are listed; an absent pin id here means
            # empty, exactly as an absent piece on the physical board does.
            "pieces": pieces,
        },
    }
