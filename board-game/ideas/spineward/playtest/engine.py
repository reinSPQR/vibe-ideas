"""engine.py — spineward, an executable model of idea.json. Not a game to play.

Board: 37 hex pans on cube coordinates (x + y + z = 0, max(|x|,|y|,|z|) <= 3).
Seed pans = the 19 cells with max(|x|,|y|,|z|) <= 2. Landing shelves = the 6
cells at distance 3 that are an exact multiple of one of the six hex
direction vectors (the "corners" of the outer ring). The other 12 outer-ring
cells are plain reef.

An urchin's six sockets are modelled as a length-6 list indexed by the
CURRENT hex direction each socket points at (not by a fixed physical socket
id), because nothing in the rules ever distinguishes one physical socket from
another — only the direction it is presently aimed at and what it holds
matter. TURN then just cyclically rotates that list; CREEP translates the
shell without touching it, which is exactly "keeps its facing".

Two actions per turn (`grow`, `shed`, `turn`, `creep`, `take`, `drop`, `rob`,
`land`) are threaded onto a single legal_moves()/apply_move() loop; setup
(`setup_seed`, `setup_place`, `setup_spine`) is real decision-making by real
players, per idea.json's setup rules, and is played through the same loop
rather than resolved inside new_game().
"""
from __future__ import annotations

import itertools
import random  # noqa: F401 - engine takes rng as an argument; no module-level use


class Undefined(Exception):
    """The rules do not say."""


SLUG = "spineward"
PLAYERS = (2, 4)
MAX_TURNS = 450
MOVE_KINDS = ("setup_seed", "setup_place", "setup_spine",
              "grow", "shed", "turn", "creep", "take", "drop", "rob", "land")
HIDDEN_INFO = True  # a pearl's grade is unknown to every seat, including its
                     # carrier, until the moment it is landed

# ---------------------------------------------------------------------------
# Assumptions
# ---------------------------------------------------------------------------
# ROB's four stated conditions (rules:turn[8]) never say what happens when all
# four hold but the target urchin is carrying zero pearls: "Take any one
# pearl from its sockets" then has nothing to take. Both readings let play
# continue, so it is declared here rather than guessed silently.
ASSUMPTIONS = [
    {"id": "rob_needs_target_pearls",
     "rule": "rules:turn[8]",
     "question": "ROB's four listed conditions do not include 'the target is "
                 "carrying at least one pearl'. If all four hold but the "
                 "target's sockets are empty, is ROB simply not offered as a "
                 "move, or is it a legal action that consumes one of your "
                 "two actions and transfers nothing?",
     "chosen": "not_legal",
     "alternative": "legal_noop"},
]
CHOICES = {"rob_needs_target_pearls": "chosen"}

# ---------------------------------------------------------------------------
# Board geometry
# ---------------------------------------------------------------------------
DIRS = ((1, -1, 0), (1, 0, -1), (0, 1, -1), (-1, 1, 0), (-1, 0, 1), (0, -1, 1))
RADIUS = 3
TOTAL_GRADES = {1: 8, 2: 5, 3: 3}  # 8 one-ring, 5 two-ring, 3 three-ring = 16


def _cube_dist(a, b) -> int:
    return max(abs(a[i] - b[i]) for i in range(3))


def _neighbor(pan, d):
    dv = DIRS[d]
    return (pan[0] + dv[0], pan[1] + dv[1], pan[2] + dv[2])


def _opposite(d):
    return (d + 3) % 6


def _all_pans():
    pans = {}
    for x in range(-RADIUS, RADIUS + 1):
        for y in range(-RADIUS, RADIUS + 1):
            z = -x - y
            if abs(z) > RADIUS:
                continue
            coord = (x, y, z)
            if _cube_dist((0, 0, 0), coord) > RADIUS:
                continue
            dist = _cube_dist((0, 0, 0), coord)
            if dist <= RADIUS - 1:
                ptype = "seed"
            else:
                is_corner = any(coord == (RADIUS * dv[0], RADIUS * dv[1], RADIUS * dv[2])
                                 for dv in DIRS)
                ptype = "shelf" if is_corner else "outer"
            pans[coord] = {"type": ptype, "pearl": None}
    return pans


def _is_pearl(content) -> bool:
    return content is not None and content != "spine"


def _is_adjacent(a, b) -> bool:
    return _cube_dist(a, b) == 1


def _urchin_at(state, pan):
    for i, u in enumerate(state["urchins"]):
        if u["pan"] == pan:
            return i
    return None


def _pan_clear(state, pan) -> bool:
    if state["pans"][pan]["pearl"] is not None:
        return False
    return _urchin_at(state, pan) is None


def _no_pearls_on_board(state) -> bool:
    return all(info["pearl"] is None for info in state["pans"].values())


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def new_game(n_players, rng):
    grades = [1] * TOTAL_GRADES[1] + [2] * TOTAL_GRADES[2] + [3] * TOTAL_GRADES[3]
    rng.shuffle(grades)
    pearl_grades = {i: grades[i] for i in range(16)}
    seed_queue = list(range(16))
    rng.shuffle(seed_queue)

    state = {
        "n": n_players,
        "phase": "seed",
        "pans": _all_pans(),
        "pearl_grades": pearl_grades,
        "pearl_location": {},   # pid -> ("pan", coord) | ("shell", seat, dir) | ("rack", seat)
        "revealed": set(),
        "seed_queue": seed_queue,
        "seed_turn": 0,
        "urchins": [{"pan": None, "dir": [None] * 6} for _ in range(n_players)],
        "racks": [[] for _ in range(n_players)],
        "spine_supply": 24,
        "setup_place_turn": 0,
        "arm_turn": 0,
        "arm_count": 0,
        "current_seat": 0,
        "actions_taken": 0,
        "turn_number": 0,
        "end_pending": False,
        "activity_flag": False,
    }
    return state


def player_to_move(state):
    phase = state["phase"]
    if phase == "seed":
        return state["seed_turn"]
    if phase == "place_shell":
        return state["setup_place_turn"]
    if phase == "arm":
        return state["arm_turn"]
    return state["current_seat"]


# ---------------------------------------------------------------------------
# legal_moves — pure, no mutation
# ---------------------------------------------------------------------------

def legal_moves(state):
    phase = state["phase"]

    if phase == "seed":
        return [("setup_seed", pan) for pan, info in state["pans"].items()
                if info["type"] == "seed" and info["pearl"] is None]

    if phase == "place_shell":
        placed = [u["pan"] for u in state["urchins"] if u["pan"] is not None]
        moves = []
        for pan, info in state["pans"].items():
            if info["type"] != "outer":
                continue
            if pan in placed:
                continue
            if any(_is_adjacent(pan, p) for p in placed):
                continue
            moves.append(("setup_place", pan))
        return moves

    if phase == "arm":
        u = state["urchins"][state["arm_turn"]]
        return [("setup_spine", d) for d in range(6) if u["dir"][d] is None]

    # phase == "main"
    seat = state["current_seat"]
    u = state["urchins"][seat]
    pan = u["pan"]
    moves = []

    if state["spine_supply"] > 0:
        for d in range(6):
            if u["dir"][d] is None:
                moves.append(("grow", d))

    for d in range(6):
        if u["dir"][d] == "spine":
            moves.append(("shed", d))

    moves.append(("turn", 1))
    moves.append(("turn", -1))

    for d in range(6):
        if u["dir"][d] != "spine":
            continue
        npan = _neighbor(pan, d)
        if npan in state["pans"] and _pan_clear(state, npan):
            moves.append(("creep", d))

    for d in range(6):
        if u["dir"][d] != "spine":
            continue
        npan = _neighbor(pan, d)
        if npan in state["pans"] and state["pans"][npan]["pearl"] is not None:
            for e in range(6):
                if u["dir"][e] is None:
                    moves.append(("take", d, e))

    held_dirs = [f for f in range(6) if _is_pearl(u["dir"][f])]
    for f in held_dirs:
        for d in range(6):
            if u["dir"][d] != "spine":
                continue
            npan = _neighbor(pan, d)
            if npan in state["pans"] and _pan_clear(state, npan):
                moves.append(("drop", f, d))

    for d in range(6):
        if u["dir"][d] != "spine":
            continue
        npan = _neighbor(pan, d)
        if npan not in state["pans"]:
            continue
        tseat = _urchin_at(state, npan)
        if tseat is None or tseat == seat:
            continue
        tgt = state["urchins"][tseat]
        if tgt["dir"][_opposite(d)] == "spine":
            continue
        target_has_pearl = any(_is_pearl(c) for c in tgt["dir"])
        if CHOICES.get("rob_needs_target_pearls", "chosen") == "chosen" \
                and not target_has_pearl:
            continue
        for e in range(6):
            if u["dir"][e] is None:
                moves.append(("rob", d, e))

    if state["pans"][pan]["type"] == "shelf" and held_dirs:
        empty_wells = 6 - len(state["racks"][seat])
        if empty_wells > 0:
            maxk = min(len(held_dirs), empty_wells)
            for k in range(1, maxk + 1):
                for combo in itertools.combinations(held_dirs, k):
                    moves.append(("land", combo))

    return moves


# ---------------------------------------------------------------------------
# apply_move — may mutate; MUST return the state
# ---------------------------------------------------------------------------

def apply_move(state, move, rng):
    kind = move[0]

    if kind == "setup_seed":
        pan = move[1]
        pid = state["seed_queue"].pop(0)
        state["pans"][pan]["pearl"] = pid
        state["pearl_location"][pid] = ("pan", pan)
        state["seed_turn"] = (state["seed_turn"] + 1) % state["n"]
        if not state["seed_queue"]:
            state["phase"] = "place_shell"
        return state

    if kind == "setup_place":
        pan = move[1]
        seat = state["setup_place_turn"]
        state["urchins"][seat]["pan"] = pan
        state["setup_place_turn"] += 1
        if state["setup_place_turn"] >= state["n"]:
            state["phase"] = "arm"
            state["arm_turn"] = state["n"] - 1
            state["arm_count"] = 0
        return state

    if kind == "setup_spine":
        d = move[1]
        seat = state["arm_turn"]
        state["urchins"][seat]["dir"][d] = "spine"
        state["spine_supply"] -= 1
        state["arm_count"] += 1
        if state["arm_count"] >= 2:
            state["arm_count"] = 0
            state["arm_turn"] -= 1
            if state["arm_turn"] < 0:
                state["phase"] = "main"
                state["current_seat"] = 0
                state["actions_taken"] = 0
                state["turn_number"] = 0
                state["end_pending"] = False
                state["activity_flag"] = False
        return state

    # main-phase actions
    seat = state["current_seat"]
    u = state["urchins"][seat]
    activity = False

    if kind == "grow":
        d = move[1]
        u["dir"][d] = "spine"
        state["spine_supply"] -= 1
    elif kind == "shed":
        d = move[1]
        u["dir"][d] = None
        state["spine_supply"] += 1
    elif kind == "turn":
        s = move[1]
        u["dir"] = [u["dir"][(d - s) % 6] for d in range(6)]
    elif kind == "creep":
        d = move[1]
        u["pan"] = _neighbor(u["pan"], d)
    elif kind == "take":
        d, e = move[1], move[2]
        npan = _neighbor(u["pan"], d)
        pid = state["pans"][npan]["pearl"]
        state["pans"][npan]["pearl"] = None
        u["dir"][e] = pid
        state["pearl_location"][pid] = ("shell", seat, e)
        activity = True
    elif kind == "drop":
        f, d = move[1], move[2]
        pid = u["dir"][f]
        u["dir"][f] = None
        npan = _neighbor(u["pan"], d)
        state["pans"][npan]["pearl"] = pid
        state["pearl_location"][pid] = ("pan", npan)
        activity = True
    elif kind == "rob":
        d, e = move[1], move[2]
        npan = _neighbor(u["pan"], d)
        tseat = _urchin_at(state, npan)
        tgt = state["urchins"][tseat]
        pearl_dirs = [f for f in range(6) if _is_pearl(tgt["dir"][f])]
        if pearl_dirs:
            f = pearl_dirs[rng.randrange(len(pearl_dirs))]
            pid = tgt["dir"][f]
            tgt["dir"][f] = None
            u["dir"][e] = pid
            state["pearl_location"][pid] = ("shell", seat, e)
        activity = True
    elif kind == "land":
        for f in move[1]:
            pid = u["dir"][f]
            u["dir"][f] = None
            state["racks"][seat].append(pid)
            state["pearl_location"][pid] = ("rack", seat)
            state["revealed"].add(pid)
        activity = True
    else:
        raise AssertionError(f"engine bug: unhandled move kind {kind!r}")

    if activity:
        state["activity_flag"] = True

    if not state["end_pending"]:
        if _no_pearls_on_board(state) or any(len(r) >= 6 for r in state["racks"]):
            state["end_pending"] = True

    state["actions_taken"] += 1
    if state["actions_taken"] >= 2:
        state["actions_taken"] = 0
        state["current_seat"] = (state["current_seat"] + 1) % state["n"]
        state["turn_number"] += 1
        if state["turn_number"] % state["n"] == 0:
            if not state["activity_flag"] and not state["end_pending"]:
                state["end_pending"] = True
            state["activity_flag"] = False

    return state


# ---------------------------------------------------------------------------
# Ending, scoring
# ---------------------------------------------------------------------------

def is_over(state) -> bool:
    if state["phase"] != "main":
        return False
    return (state["end_pending"] and state["actions_taken"] == 0
            and state["turn_number"] > 0 and state["turn_number"] % state["n"] == 0)


def scores(state):
    return [float(sum(state["pearl_grades"][pid] for pid in rack))
            for rack in state["racks"]]


def winners(state):
    totals = scores(state)
    if not totals:
        return []
    top = max(totals)
    cands = [i for i, v in enumerate(totals) if v == top]
    if len(cands) == 1:
        return cands

    counts = [len(state["racks"][i]) for i in range(state["n"])]
    topc = max(counts[i] for i in cands)
    cands2 = [i for i in cands if counts[i] == topc]
    if len(cands2) == 1:
        return cands2

    spines = [sum(1 for c in state["urchins"][i]["dir"] if c == "spine")
              for i in range(state["n"])]
    tops = max(spines[i] for i in cands2)
    return [i for i in cands2 if spines[i] == tops]


# ---------------------------------------------------------------------------
# Hidden information
# ---------------------------------------------------------------------------

def determinize(state, seat, rng):
    """Resample every unrevealed pearl's grade, uniformly over what remains.

    No seat, including a pearl's own carrier, ever learns a grade before it
    is landed (rules:turn[9]: "you do not look at its foot and nor does
    anyone else"), so every seat's uncertainty is identical and this ignores
    `seat` beyond the signature the harness expects.
    """
    revealed_counts = {1: 0, 2: 0, 3: 0}
    for pid in state["revealed"]:
        revealed_counts[state["pearl_grades"][pid]] += 1
    pool = []
    for g in (1, 2, 3):
        pool.extend([g] * (TOTAL_GRADES[g] - revealed_counts[g]))
    rng.shuffle(pool)
    unrevealed = [pid for pid in range(16) if pid not in state["revealed"]]
    for pid, g in zip(unrevealed, pool):
        state["pearl_grades"][pid] = g
    return state
