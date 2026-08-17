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
ASSUMPTIONS = []       # no reading found where BOTH branches let play continue;
CHOICES = {}            # see notes.md for the two genuine Undefined gaps instead


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


def _build_adj(state):
    pins = state["pins"]
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
    _, _, bound = _analyze_graph(_build_adj(state))
    return bound


# ---------------------------------------------------------------------------
# Setup (rules:setup[3..4])
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
        # rules:turn[1] — any other empty yard pin, or leave it where it is.
        moves = [("power", p) for p in YARD_PINS if pins[p] is None]
        moves.append(("power", state["crank_pin"]))
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
        state["setup_index"] += 1
        if state["setup_index"] >= state["n_players"]:
            state["phase"] = "setup_crank"
        return state

    if kind == "setup_crank":
        pin = move[1]
        state["pins"][pin] = {"type": "crank"}
        state["crank_pin"] = pin
        state["phase"] = "power"
        return state

    if kind == "power":
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
# THE GRIND (rules:turn[7]) and DIRECTION (rules:turn[8])
# ---------------------------------------------------------------------------

def _process_grind(state):
    adj = _build_adj(state)
    color, comp, bound = _analyze_graph(adj)

    if bound:
        # rules:turn[1] POWER lets the start player move the crank to any
        # empty yard pin with no bind test at all — rules:turn[5] TEST FOR
        # A BIND is scoped explicitly to "Immediately after a PLACE or a
        # SHIFT". A crank relocation can still close an odd loop through
        # its own meshed cluster (it changes every edge incident to the
        # crank's new pin), and once that happens every PLACE/SHIFT this
        # round finds the whole graph already bound and reverts, so
        # nothing can fix it before rules:turn[7] THE GRIND, which assumes
        # the crank always completes one full clockwise turn. The rules
        # never say whether POWER should have been bind-tested too,
        # whether the round simply grinds nothing, or something else.
        raise Undefined(
            "rules:turn[7]: THE GRIND assumes the crank always completes "
            "one full clockwise turn, but rules:turn[1] POWER moves the "
            "crank_gear with no bind test (rules:turn[5] TEST FOR A BIND "
            "only covers a PLACE or a SHIFT), and this round the crank's "
            "pin closed an odd loop through its own meshed cluster, so the "
            "crank cannot physically complete the turn this step calls for."
        )

    crank_pin = state["crank_pin"]
    crank_color = color.get(crank_pin)
    crank_comp = comp.get(crank_pin)

    cw_seats = []
    for seat in range(state["n_players"]):
        mp = state["mill_pin"][seat]
        if mp is not None and comp.get(mp) == crank_comp and color.get(mp) == crank_color:
            cw_seats.append(seat)

    need = 2 if len(cw_seats) == 1 else len(cw_seats)
    if need > state["pellets"]:
        # rules:end[1] ends the game "at the end of the round in which the
        # granary_bin is emptied", which only cleanly covers a payout that
        # exactly exhausts it. rules:turn[7] never says how to divide a
        # granary that runs out mid-payout, e.g. two millstones owed one
        # pellet each with only one left in the bin.
        raise Undefined(
            "rules:turn[7]/end[1]: THE GRIND owes "
            f"{need} grain_pellet this round (one per clockwise millstone, "
            f"two if exactly one turned) but only {state['pellets']} remain "
            "in the granary_bin, and the rules never say how a payout that "
            "the bin cannot cover should be divided."
        )

    reward = 2 if len(cw_seats) == 1 else 1
    for seat in cw_seats:
        state["spindles"][seat] += reward
    state["pellets"] -= need
    state["last_grind_cw"] = list(cw_seats)

    supply_empty = all(v == 0 for v in state["supply"].values())
    # rules:end[0] / rules:end[1]
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
