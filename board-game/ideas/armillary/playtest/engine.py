"""engine.py — armillary, an executable model of idea.json. Not a game to play."""
import random  # only for type hints/back-compat; the rng is always passed in


class Undefined(Exception):
    """The rules do not say."""


SLUG = "armillary"
PLAYERS = (2, 4)
MAX_TURNS = 500
# Every action the rules define. BANK and REFILL are automatic consequences
# (folded into "stop"/"take"/"clear"/"forfeit"), never a player choice, so
# they are not their own kind.
MOVE_KINDS = ("turn", "take", "stop", "clear", "forfeit")
HIDDEN_INFO = True

# ---------------------------------------------------------------------------
# Assumptions the prose leaves open. Both readings let play continue; the
# harness plays both and reports whether the choice is load-bearing.
# ---------------------------------------------------------------------------

ASSUMPTIONS = [
    {
        "id": "clear_repeat",
        "rule": "rules:turn[5]",
        "question": "CLEAR says a stuck player 'may instead lift one "
                    "face-up void_tile ... That well counts as empty,' "
                    "framed as a single substitute for the reach step. If "
                    "several face-up void_tiles sit on the board, may the "
                    "player lift more than one of them in the same stuck "
                    "turn, or does performing CLEAR once end the reach "
                    "step exactly as BANK would?",
        "chosen": "one clear ends the reach step for the turn (bank "
                  "nothing caught so far, refill, pass)",
        "alternative": "clear may be repeated against every remaining "
                       "face-up void_tile before the reach step ends",
    },
]
CHOICES = {"clear_repeat": "chosen"}

# ---------------------------------------------------------------------------
# Board geometry: ten wells at index grooves 0..9. Each mask disc's window
# set is its NATIVE groove positions when its witness notch points at groove
# 0 (setup). A disc's current rotation offset is added to every native
# window position (mod 10) to find which grooves it currently covers. A well
# is open only where all three discs' covered sets intersect — computed from
# the rotations, never hard-coded to "which wells are open".
# ---------------------------------------------------------------------------

DISCS = ("a", "b", "c")
DELTAS = (-3, -2, -1, 1, 2, 3)
WINDOWS = {
    "a": frozenset({0, 1, 2, 3, 4, 6}),
    "b": frozenset({0, 1, 2, 3, 6, 7}),
    "c": frozenset({0, 1, 3, 5, 6, 8}),
}
ZENITH_WELLS = frozenset({0, 4, 7})

STAR_QTY, MOON_QTY, VOID_QTY = 12, 10, 8
TILE_VALUE = {"star": 2.0, "moon": 1.0}


def _open_wells(state):
    result = None
    rot = state["rotation"]
    for d in DISCS:
        r = rot[d]
        covered = {(p + r) % 10 for p in WINDOWS[d]}
        result = covered if result is None else (result & covered)
    return result


def _takeable_wells(state):
    """Open wells holding a tile that REACH permits taking: any knob-up
    (face-down) tile (risky), or an already face-up star/moon (free). A
    face-up void_tile blocks its well from REACH; only CLEAR can move it."""
    out = []
    for w in _open_wells(state):
        cell = state["wells"][w]
        if cell is None:
            continue
        if cell["face"] == "down":
            out.append(w)
        elif cell["face"] == "up" and cell["tile"] in ("star", "moon"):
            out.append(w)
    return out


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def new_game(n_players, rng):
    pool = ["star"] * STAR_QTY + ["moon"] * MOON_QTY + ["void"] * VOID_QTY
    rng.shuffle(pool)
    wells = [{"tile": pool[i], "face": "down"} for i in range(10)]
    reserve = pool[10:]
    return {
        "n_players": n_players,
        "rotation": {"a": 0, "b": 0, "c": 0},
        "wells": wells,
        "reserve": reserve,
        "banks": [[] for _ in range(n_players)],
        "catch": [],          # [(well, tile_type, is_zenith), ...] this reach
        "phase": "turn",      # "turn" | "reach" | "forfeit"
        "current": 0,
    }


def player_to_move(state):
    return state["current"]


# ---------------------------------------------------------------------------
# Moves
# ---------------------------------------------------------------------------

def legal_moves(state):
    phase = state["phase"]
    if phase == "turn":
        # TURN THE SKY is compulsory but always has options: every disc can
        # always turn 1-3 grooves either way (a 10-groove ring wraps).
        return [("turn", d, delta) for d in DISCS for delta in DELTAS]

    if phase == "reach":
        takeable = _takeable_wells(state)
        moves = [("take", w) for w in sorted(takeable)]
        moves.append(("stop",))
        # CLEAR only applies "right after your rotation" (catch still
        # empty this reach) and only when stuck (nothing takeable at all).
        if not state["catch"] and not takeable:
            void_targets = [
                w for w in range(10)
                if state["wells"][w] is not None
                and state["wells"][w]["face"] == "up"
                and state["wells"][w]["tile"] == "void"
            ]
            moves.extend(("clear", w) for w in sorted(void_targets))
        return moves

    if phase == "forfeit":
        # Triggered only when the busting player's score_rail is non-empty,
        # so this is never offered with zero options.
        bank = state["banks"][state["current"]]
        return [("forfeit", i) for i in range(len(bank))]

    return []


def apply_move(state, move, rng):
    kind = move[0]

    if kind == "turn":
        _, disc, delta = move
        state["rotation"][disc] = (state["rotation"][disc] + delta) % 10
        state["phase"] = "reach"
        state["catch"] = []
        return state

    if kind == "take":
        _, w = move
        return _apply_take(state, w, rng)

    if kind == "stop":
        # "If you stop before busting, or run out of open wells holding a
        # takeable tile" both land here — from the engine's point of view
        # neither is a further branch, both just bank whatever was caught.
        return _end_turn(state)

    if kind == "clear":
        _, w = move
        state["wells"][w] = None  # void tile returned to the box
        if CHOICES.get("clear_repeat", "chosen") != "alternative":
            return _end_turn(state)
        return state

    if kind == "forfeit":
        _, idx = move
        bank = state["banks"][state["current"]]
        if 0 <= idx < len(bank):
            bank.pop(idx)
        return _end_turn(state)

    raise Undefined(f"engine: move kind {kind!r} is not one the rules define")


def _apply_take(state, w, rng):
    cell = state["wells"][w]
    ttype = cell["tile"]
    was_facedown = cell["face"] == "down"
    is_zenith = w in ZENITH_WELLS

    if ttype == "void" and was_facedown:
        # BUST. The void stays face-up in its own well forever; every tile
        # in this reach's catch goes back face-up to the well it came from.
        state["wells"][w] = {"tile": "void", "face": "up"}
        for (ow, ot, oz) in state["catch"]:
            state["wells"][ow] = {"tile": ot, "face": "up"}
        state["catch"] = []
        if is_zenith:
            bank = state["banks"][state["current"]]
            if bank:
                state["phase"] = "forfeit"
                return state
            # Nothing on the rail to forfeit: the penalty has no target.
            # The rules only ever describe taking a tile that is there;
            # there is exactly one sensible reading when there isn't one,
            # not two, so this is not a declared assumption.
        return _end_turn(state)

    # A free face-up star/moon, or a knob-up tile that turned out to be
    # star/moon: joins the catch, still exposed to a later bust this turn.
    state["catch"].append((w, ttype, is_zenith))
    state["wells"][w] = None
    return state


def _end_turn(state):
    bank = state["banks"][state["current"]]
    for (_w, t, z) in state["catch"]:
        bank.append({"type": t, "zenith": z})
    state["catch"] = []
    for w in range(10):
        if state["wells"][w] is None and state["reserve"]:
            t = state["reserve"].pop()
            state["wells"][w] = {"tile": t, "face": "down"}
    state["current"] = (state["current"] + 1) % state["n_players"]
    state["phase"] = "turn"
    return state


# ---------------------------------------------------------------------------
# End of game
# ---------------------------------------------------------------------------

def is_over(state):
    # "It also ends immediately if every one of the ten wells holds a
    # face-up tile" — checked live, any phase, any time.
    if all(c is not None and c["face"] == "up" for c in state["wells"]):
        return True
    # "The game ends at the end of the turn on which the reserve_column is
    # empty and no well holds a knob-up tile" — a turn-boundary condition,
    # so only checked when the next player is about to TURN THE SKY. Checked
    # mid-reach it would wrongly end the game while a catch is still on the
    # table waiting to be banked or busted.
    if state["phase"] == "turn":
        if not state["reserve"] and not any(
            c is not None and c["face"] == "down" for c in state["wells"]
        ):
            return True
    return False


def scores(state):
    out = []
    for bank in state["banks"]:
        total = 0.0
        for item in bank:
            total += TILE_VALUE.get(item["type"], 0.0)
            if item["zenith"]:
                total += 1.0
        out.append(total)
    return out


def winners(state):
    sc = scores(state)
    if not sc:
        return []
    top = max(sc)
    tied = [i for i, s in enumerate(sc) if s == top]
    if len(tied) <= 1:
        return tied
    star_counts = {i: sum(1 for it in state["banks"][i] if it["type"] == "star")
                   for i in tied}
    top_star = max(star_counts.values())
    return [i for i in tied if star_counts[i] == top_star]


# ---------------------------------------------------------------------------
# Hidden information. No seat has a private hand — every face-down tile
# (in a well or still in the reserve stack) is equally unknown to everyone.
# determinize reshuffles only those unrevealed identities among themselves,
# preserving the remaining star/moon/void counts, so a lookahead policy
# cannot read the tiles' faces from the ground-truth state.
# ---------------------------------------------------------------------------

def determinize(state, seat, rng):
    import copy
    s = copy.deepcopy(state)
    slots = []
    types = []
    for w in range(10):
        cell = s["wells"][w]
        if cell is not None and cell["face"] == "down":
            slots.append(("well", w))
            types.append(cell["tile"])
    for i in range(len(s["reserve"])):
        slots.append(("reserve", i))
        types.append(s["reserve"][i])
    rng.shuffle(types)
    for (kind, idx), t in zip(slots, types):
        if kind == "well":
            s["wells"][idx]["tile"] = t
        else:
            s["reserve"][idx] = t
    return s


def observation(state, seat):
    """What `seat` is actually allowed to look at. No seat holds a private
    hand in this game — the only concealment is the shared board's face-down
    tiles — so this observation is the same for every seat: everything
    public, and nothing else. A face-down well shows only that it holds
    *something*, not what; the reserve shows only how many tiles are left in
    it, not their order or identity."""
    wells = []
    for cell in state["wells"]:
        if cell is None:
            wells.append(None)
        elif cell["face"] == "up":
            wells.append({"tile": cell["tile"], "face": "up"})
        else:
            wells.append({"tile": None, "face": "down"})  # identity hidden
    return {
        "seat": seat,
        "n_players": state["n_players"],
        "phase": state["phase"],
        "current": state["current"],
        "rotation": dict(state["rotation"]),
        "open_wells": sorted(_open_wells(state)),
        "wells": wells,
        "reserve_count": len(state["reserve"]),
        "catch": list(state["catch"]),
        "banks": [list(b) for b in state["banks"]],
        "scores": scores(state),
    }
