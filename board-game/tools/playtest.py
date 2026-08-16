#!/usr/bin/env python3
"""playtest.py — gate R1c, the empirical half of "is this a game?". No LLM.

    python3 board-game/tools/playtest.py board-game/ideas/<slug>

`rules_check.py` proves the rules and the bill describe the same game.
`board-game-lens-rules` reads the rules and gives an opinion. Neither one
plays. Both surviving lens reviews in this repo end by deferring their real
doubts to a playtest that did not exist:

    blindcap:  "Watch item for playtest, not a failure ... it should be measured."
    spineward: "should be re-examined during playtest."

This is that playtest. It does not ask a model whether the game was fun. It
loads an executable model of the rules, plays it several thousand times with
scripted policies of increasing strength, and reports numbers.

## The engine, and why writing it is half the value

An agent (`board-game-rules-engineer`) turns `idea.json` into
`<idea>/playtest/engine.py`. Every place the rules do not say what happens is
a place that agent cannot write a branch, and the discipline is that it must
NOT guess: it either raises `Undefined("rules:turn[5]: ...")` at that point, or
registers the guess in `ASSUMPTIONS` so this harness can play the game both
ways and see whether the reading matters. A rules gap found while writing the
engine is worth more than any number below, because it comes with the exact
rule that has to be rewritten.

The engine contract, all of it:

    SLUG        = "millbind"
    PLAYERS     = (2, 4)          # seat counts the engine supports
    MAX_TURNS   = 400             # the author's own cap on a sane game
    MOVE_KINDS  = ("place", "shift", "pass")   # every action the rules define
    HIDDEN_INFO = False           # does any seat know something another does not?
    ASSUMPTIONS = [{"id": "shift_adjacency", "rule": "rules:turn[5]",
                    "question": "may a mill shift onto a pin adjacent to another mill?",
                    "chosen": "yes", "alternative": "no"}]
    CHOICES     = {"shift_adjacency": "chosen"}   # this harness flips these

    new_game(n_players, rng) -> state
    player_to_move(state)    -> seat index
    legal_moves(state)       -> list of moves, each with a `.kind` str
    apply_move(state, move, rng) -> state   (may mutate; must return it)
    is_over(state)           -> bool
    scores(state)            -> list of floats, one per seat, valid any time
    winners(state)           -> list of seat indices, valid once over

    determinize(state, seat, rng) -> state    # OPTIONAL, hidden-information
                                              # games only: resample what
                                              # `seat` cannot see

Without `determinize`, a lookahead policy in a hidden-information game is an
oracle that can see the face-down tiles, so its win rate would be an upper
bound rather than a skill measurement. `HIDDEN_INFO` is declared separately
from `determinize` existing precisely so that the harness can tell "this game
has nothing to hide" apart from "this engine forgot to hide it".

## What the numbers mean

- **termination** — every playout must reach a natural end. Anything else is a
  game that can hang at a real table.
- **deadlock** — a position with no legal move and no ending. Almost always a
  rule that forgot to say "if you cannot act, pass".
- **decisions** — how many legal moves a turn really offers, and how often the
  answer is exactly one. A turn with one option is not a turn.
- **depth** — the skill ladder: random, then greedy, then flat Monte Carlo. If
  a policy that looks a full game ahead cannot beat one throwing dice, there is
  nothing to be good at. This is the strongest single measure here.
- **seat bias** — identical policies, all seats, thousands of games. This is
  the one that Deep Claim died of, in the owner's own words: "an optimal
  strategy for the first player to always win".
- **runaway** — how often whoever leads at the halfway point simply wins.
- **length** — real turn counts against `playtime_min`.
- **dead moves** — an action the rules define, that is legal, and that the
  strongest policy never once chooses.
- **sensitivity** — each declared assumption played both ways. If flipping it
  moves the headline numbers, the ambiguity is blocking and the rules have to
  settle it. If nothing moves, it is cosmetic and can be left alone.

Exit 0 = PASS, 1 = FAIL, 2 = the engine itself is broken or missing (which is
not a verdict on the game). `--report-only` always exits 0: that is shadow
mode, for running the gate before its thresholds have been calibrated.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import random
import statistics
import sys
import time
import traceback
from pathlib import Path
from types import ModuleType

# ---------------------------------------------------------------------------
# Thresholds — UNCALIBRATED. Every one of these is a guess until it has been
# backtested against the ideas whose answer is already known: Millbind shipped,
# Deep Claim was killed by the owner for a first-player win. A threshold that
# cannot separate those two is not a threshold, it is decoration.
# ---------------------------------------------------------------------------

# A turn offering one legal move is not a turn. Some are fine (forced recapture,
# a mandatory upkeep step); a quarter of the game is not.
MAX_FORCED_FRACTION = 0.25

# Median options per turn. Two is a coin flip wearing a hat.
MIN_MEDIAN_BRANCHING = 3.0

# How far the strongest policy must beat random, above its fair share of wins,
# for the game to contain a skill worth having.
MIN_SKILL_EDGE = 0.15

# How far any one seat may sit above its fair share, with identical policies in
# every seat, before the seat itself is the strategy.
MAX_SEAT_EDGE = 0.10

# Whoever leads at the halfway mark will usually win; a game where they ALWAYS
# win stopped being a game at the halfway mark.
MAX_RUNAWAY = 0.85

# A shared win now and then is fine. A quarter of all games ending level means
# the tiebreaker does not break ties.
MAX_TIE_RATE = 0.25

# One decision at a real table, including the hand movement it causes. A
# range, not a number: rotating one disc and choosing among 60 gear placements
# on a board you then have to crank and inspect are not the same twenty
# seconds, and this file has no way to tell them apart. The length check is
# deliberately loose because of it, and only fires on a claim no plausible
# pace can reach.
SECONDS_PER_DECISION = (8.0, 25.0)
LENGTH_TOLERANCE = (0.5, 2.5)

# A win rate on eight games is not a win rate. Below this a ladder rung is
# reported and then ignored by the depth verdict.
MIN_LADDER_GAMES = 20

# Above this share of games ending in a rules gap, nothing else measured is
# worth reading: the sample is whatever subset of the game the rules happened
# to cover, which is not the game.
MAX_UNDEFINED_SHARE = 0.15

# A flipped assumption that moves any headline number by more than this is
# load-bearing, and the rules have to say which reading is meant.
SENSITIVITY_DELTA = 0.10

# Playouts. Volume is cheap for the scripted policies and expensive for the
# lookahead one, so they get separate counts.
DEFAULT_GAMES = 400
DEFAULT_LADDER_GAMES = 120
DEFAULT_MC_BUDGET = 240   # rollouts per decision, split across the legal moves
DEFAULT_DEADLINE = 900.0  # seconds for the whole run


REQUIRED_CALLS = ("new_game", "player_to_move", "legal_moves", "apply_move",
                  "is_over", "scores", "winners")
REQUIRED_META = ("PLAYERS", "MAX_TURNS", "HIDDEN_INFO")


# ---------------------------------------------------------------------------
# Loading and validating an engine
# ---------------------------------------------------------------------------

class EngineBroken(Exception):
    """The engine is not a usable model of the rules. Not a verdict on the game."""


def load_engine(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"pt_engine_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise EngineBroken(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - any import error is the same problem
        raise EngineBroken(f"{path} failed to import: {exc}") from exc
    return module


def validate_engine(eng: ModuleType) -> list[str]:
    findings = []
    for name in REQUIRED_CALLS:
        if not callable(getattr(eng, name, None)):
            findings.append(f"contract: engine has no callable `{name}`")
    for name in REQUIRED_META:
        if getattr(eng, name, None) is None:
            findings.append(f"contract: engine has no `{name}`")
    players = getattr(eng, "PLAYERS", None)
    if players is not None:
        try:
            lo, hi = int(players[0]), int(players[1])
            if lo < 1 or hi < lo:
                findings.append(f"contract: PLAYERS {players} is not a seat range")
        except (TypeError, ValueError, IndexError):
            findings.append(f"contract: PLAYERS {players!r} is not (min, max)")
    for entry in getattr(eng, "ASSUMPTIONS", []) or []:
        missing = [k for k in ("id", "rule", "question", "chosen", "alternative")
                   if not entry.get(k)]
        if missing:
            findings.append(f"contract: ASSUMPTIONS entry {entry.get('id', '?')} "
                            f"is missing {missing}")
    return findings


def is_undefined(exc: BaseException) -> bool:
    """An engine signals a rules gap with any exception class named Undefined.

    Matched by name rather than by identity so the engine stays a standalone
    file with no import back into this harness: an agent writing one should
    need nothing but `idea.json` and the contract in this docstring.
    """
    return any(cls.__name__ == "Undefined" for cls in type(exc).__mro__)


def move_kind(move) -> str:
    kind = getattr(move, "kind", None)
    if isinstance(kind, str) and kind:
        return kind
    if isinstance(move, (tuple, list)) and move and isinstance(move[0], str):
        return move[0]
    text = str(move)
    return text.split(":")[0].split("(")[0].strip()[:40] or "?"


# ---------------------------------------------------------------------------
# Policies. Each takes (engine, state, seat, rng) and returns one legal move.
# They know nothing about any particular game, which is the point: a heuristic
# tuned per game would measure the heuristic, not the game.
# ---------------------------------------------------------------------------

def _margin(scores: list, seat: int) -> float:
    """Own score minus the best rival's. What every player actually wants."""
    others = [s for i, s in enumerate(scores) if i != seat]
    return float(scores[seat]) - (max(others) if others else 0.0)


def _payoff(eng: ModuleType, state, seat: int) -> float:
    """1 for a win, split for a shared win, 0 for a loss."""
    if not eng.is_over(state):
        return 0.5  # cut short by a cap; treat as a draw rather than a loss
    winners = list(eng.winners(state))
    if not winners:
        return 0.5
    return (1.0 / len(winners)) if seat in winners else 0.0


def pol_random(eng, state, seat, rng, moves):
    return rng.choice(moves)


def pol_first(eng, state, seat, rng, moves):
    """Always the first move offered. A baseline, and an ordering-bias probe."""
    return moves[0]


def pol_greedy(eng, state, seat, rng, moves):
    """One ply: the move leaving the best score margin right now."""
    best, best_val = [], None
    for move in moves:
        after = eng.apply_move(copy.deepcopy(state), move, rng)
        val = _margin(eng.scores(after), seat)
        if best_val is None or val > best_val:
            best, best_val = [move], val
        elif val == best_val:
            best.append(move)
    return rng.choice(best)


def make_mc(budget: int, cap: int):
    """Flat Monte Carlo: play each candidate move out at random, many times.

    Deliberately the dumbest strong player there is. It needs no evaluation
    function, so it cannot be tuned to flatter a particular game, and it
    measures exactly the thing in question: does looking ahead help at all?
    """
    def pol_mc(eng, state, seat, rng, moves):
        per_move = max(1, budget // max(1, len(moves)))
        best, best_val = [], None
        for move in moves:
            total = 0.0
            for _ in range(per_move):
                trial = copy.deepcopy(state)
                determinize = getattr(eng, "determinize", None)
                if determinize is not None:
                    trial = determinize(trial, seat, rng)
                trial = eng.apply_move(trial, move, rng)
                trial, _turns, _stuck = _rollout(eng, trial, rng, cap)
                total += _payoff(eng, trial, seat)
            val = total / per_move
            if best_val is None or val > best_val:
                best, best_val = [move], val
            elif val == best_val:
                best.append(move)
        return rng.choice(best)
    return pol_mc


def _rollout(eng, state, rng, cap: int):
    """Random play to the end. Returns (state, turns played, stuck)."""
    turns = 0
    while turns < cap and not eng.is_over(state):
        moves = eng.legal_moves(state)
        if not moves:
            return state, turns, True
        state = eng.apply_move(state, rng.choice(moves), rng)
        turns += 1
    return state, turns, False


# ---------------------------------------------------------------------------
# One game
# ---------------------------------------------------------------------------

def play_one(eng: ModuleType, seat_policies: list, n_players: int,
             rng: random.Random, cap: int) -> dict:
    """Play a single game. Never raises for a game-level fault; reports it."""
    record = {
        "turns": 0, "natural": False, "stuck": False, "undefined": None,
        "winners": [], "scores": [], "branching": [], "kinds_chosen": [],
        "kinds_legal": set(), "leader_at_half": None,
    }
    try:
        state = eng.new_game(n_players, rng)
        seen: list[list] = []
        while record["turns"] < cap:
            if eng.is_over(state):
                record["natural"] = True
                break
            moves = eng.legal_moves(state)
            record["branching"].append(len(moves))
            for move in moves:
                record["kinds_legal"].add(move_kind(move))
            if not moves:
                record["stuck"] = True
                break
            seat = int(eng.player_to_move(state))
            move = seat_policies[seat](eng, state, seat, rng, moves)
            record["kinds_chosen"].append(move_kind(move))
            state = eng.apply_move(state, move, rng)
            seen.append(list(eng.scores(state)))
            record["turns"] += 1
    except Exception as exc:  # noqa: BLE001
        if is_undefined(exc):
            record["undefined"] = str(exc)
            return record
        raise EngineBroken(
            f"engine raised {type(exc).__name__}: {exc}\n"
            + "".join(traceback.format_exc(limit=6))) from exc

    record["scores"] = list(eng.scores(state))
    record["winners"] = list(eng.winners(state)) if record["natural"] else []
    if seen:
        half = seen[len(seen) // 2]
        top = max(half)
        leaders = [i for i, s in enumerate(half) if s == top]
        record["leader_at_half"] = leaders[0] if len(leaders) == 1 else None
    return record


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------

def wilson(hits: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Confidence interval on a win rate. A win rate with no interval on it is
    an anecdote with a decimal point."""
    if total == 0:
        return (0.0, 1.0)
    p = hits / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def run_batch(eng, policy_of_seat, n_players: int, games: int, cap: int,
              seed: int, deadline: float, challenger_seat=None) -> dict:
    """`policy_of_seat(seat, game_index)` picks each seat's policy per game, so
    a challenger can be rotated through every seat and never gain or lose from
    where it sat. `challenger_seat(game_index)` says which seat that was, and
    is the only way the challenger's own win rate can be read back out of a
    table where it moved around."""
    rng_master = random.Random(seed)
    challenger_wins = 0.0
    challenger_decided = 0
    wins = [0.0] * n_players
    played = natural = stuck = 0
    turns, branching, margins = [], [], []
    ties = 0
    kinds_chosen: dict[str, int] = {}
    kinds_legal: set = set()
    undefined: list[str] = []
    leader_half_correct = leader_half_seen = 0

    for i in range(games):
        if time.monotonic() > deadline:
            break
        rng = random.Random(rng_master.randrange(1 << 30))
        seats = [policy_of_seat(s, i) for s in range(n_players)]
        rec = play_one(eng, seats, n_players, rng, cap)
        played += 1
        if rec["undefined"]:
            undefined.append(rec["undefined"])
            continue
        turns.append(rec["turns"])
        branching.extend(rec["branching"])
        kinds_legal |= rec["kinds_legal"]
        for kind in rec["kinds_chosen"]:
            kinds_chosen[kind] = kinds_chosen.get(kind, 0) + 1
        if rec["stuck"]:
            stuck += 1
            continue
        if not rec["natural"]:
            continue
        natural += 1
        if len(rec["winners"]) > 1:
            ties += 1
        for seat in rec["winners"]:
            wins[seat] += 1.0 / len(rec["winners"])
        if challenger_seat is not None:
            mine = challenger_seat(i)
            challenger_decided += 1
            if mine in rec["winners"]:
                challenger_wins += 1.0 / len(rec["winners"])
        if rec["scores"]:
            ordered = sorted(rec["scores"], reverse=True)
            margins.append(ordered[0] - (ordered[1] if len(ordered) > 1 else 0))
        if rec["leader_at_half"] is not None:
            leader_half_seen += 1
            if rec["leader_at_half"] in rec["winners"]:
                leader_half_correct += 1

    return {
        "games_requested": games, "games_played": played,
        "natural_endings": natural, "stuck": stuck,
        "undefined": undefined[:5], "undefined_count": len(undefined),
        "wins": wins,
        "turns_mean": statistics.fmean(turns) if turns else 0.0,
        "turns_median": statistics.median(turns) if turns else 0.0,
        "turns_p90": (sorted(turns)[int(0.9 * (len(turns) - 1))] if turns else 0.0),
        "branching_mean": statistics.fmean(branching) if branching else 0.0,
        "branching_median": statistics.median(branching) if branching else 0.0,
        "forced_fraction": (sum(1 for b in branching if b <= 1) / len(branching)
                            if branching else 0.0),
        "margin_mean": statistics.fmean(margins) if margins else 0.0,
        "kinds_legal": sorted(kinds_legal),
        "kinds_chosen": kinds_chosen,
        "runaway": (leader_half_correct / leader_half_seen
                    if leader_half_seen else None),
        "ties": ties,
        "tie_rate": (ties / natural) if natural else 0.0,
        "challenger_wins": challenger_wins,
        "challenger_decided": challenger_decided,
    }


def seat_edge(batch: dict, n_players: int) -> dict:
    """How far the luckiest seat sits above its fair share, with the interval."""
    decided = sum(batch["wins"])
    fair = 1.0 / n_players
    rates = [(w / decided if decided else 0.0) for w in batch["wins"]]
    best = max(range(n_players), key=lambda s: rates[s]) if decided else 0
    lo, hi = wilson(int(round(batch["wins"][best])), int(round(decided)))
    return {"fair_share": fair, "win_rates": rates, "best_seat": best,
            "best_rate": rates[best] if decided else 0.0,
            "best_ci": [lo, hi], "decided": decided,
            # The edge is measured on the low end of the interval: a seat is
            # only guilty if even the pessimistic reading puts it ahead.
            "edge": (lo - fair) if decided else 0.0}


def challenge(eng, name: str, challenger, field_name: str, field,
              n_players: int, games: int, cap: int, seed: int,
              deadline: float) -> dict:
    """One policy against a table of another, rotated through every seat.

    Rotation is not politeness. Without it a challenger measured only in seat 0
    reports the seat's advantage as its own skill, and the two things this
    whole file exists to tell apart would be added together.
    """
    def policy_of_seat(seat: int, game: int):
        return challenger if seat == (game % n_players) else field

    batch = run_batch(eng, policy_of_seat, n_players, games, cap, seed,
                      deadline, challenger_seat=lambda game: game % n_players)
    won, decided = batch["challenger_wins"], batch["challenger_decided"]
    rate = (won / decided) if decided else 0.0
    lo, hi = wilson(int(round(won)), decided)
    fair = 1.0 / n_players
    return {"policy": name, "field": field_name, "games": decided,
            "win_rate": rate, "ci": [lo, hi], "fair_share": fair,
            "edge": (lo - fair) if decided else 0.0,
            "kinds_chosen": batch["kinds_chosen"]}


# ---------------------------------------------------------------------------
# The run plan
# ---------------------------------------------------------------------------

def analyse(eng: ModuleType, idea: dict, *, games: int, ladder_games: int,
            mc_budget: int, seed: int, deadline_s: float) -> dict:
    """Everything the report is made of. Raises EngineBroken, nothing else."""
    started = time.monotonic()
    deadline = started + deadline_s
    cap = int(getattr(eng, "MAX_TURNS", 400))
    lo, hi = (int(v) for v in eng.PLAYERS)
    counts = sorted({lo, hi})

    mc = make_mc(mc_budget, cap)
    seats: dict[str, dict] = {}
    for n in counts:
        # Two baselines. All-random is the purely structural read: a seat that
        # wins with nobody trying is the board's fault, not a strategy. All-
        # greedy is the same question once everyone is at least awake.
        rnd = run_batch(eng, lambda s, g: pol_random, n, games, cap,
                        seed + 11 * n, deadline)
        grd = run_batch(eng, lambda s, g: pol_greedy, n, games, cap,
                        seed + 13 * n, deadline)
        seats[str(n)] = {
            "random": {**rnd, "seat": seat_edge(rnd, n)},
            "greedy": {**grd, "seat": seat_edge(grd, n)},
        }

    table = counts[-1]
    ladder = [
        challenge(eng, "first", pol_first, "random", pol_random, table,
                  ladder_games, cap, seed + 101, deadline),
        challenge(eng, "greedy", pol_greedy, "random", pol_random, table,
                  ladder_games, cap, seed + 103, deadline),
        challenge(eng, "lookahead", mc, "random", pol_random, table,
                  ladder_games, cap, seed + 107, deadline),
        challenge(eng, "lookahead", mc, "greedy", pol_greedy, table,
                  ladder_games, cap, seed + 109, deadline),
    ]

    # Move kinds. `MOVE_KINDS` is what the rules define; what turned out to be
    # legal, and what a competent policy ever bothered to choose, are two
    # separate ways for a rule to be dead on the table.
    # Read off the all-greedy baseline alone. The ladder batches mix a
    # challenger with a field of random players in one tally, so a kind chosen
    # there may only ever have been chosen by the dice.
    declared = list(getattr(eng, "MOVE_KINDS", []) or [])
    legal = set(seats[str(table)]["greedy"]["kinds_legal"])
    chosen = set(seats[str(table)]["greedy"]["kinds_chosen"])
    moves = {
        "declared": declared,
        "never_legal": sorted(k for k in declared if k not in legal),
        "never_chosen": sorted(k for k in legal if k not in chosen),
    }

    sensitivity = run_sensitivity(eng, table, max(games // 4, 40), cap,
                                  seed + 211, deadline, pol_greedy)

    return {
        "slug": idea.get("slug") or getattr(eng, "SLUG", "?"),
        "idea": {"playtime_min": int(idea.get("playtime_min") or 0),
                 "players": [lo, hi]},
        "config": {"games": games, "ladder_games": ladder_games,
                   "mc_budget": mc_budget, "seed": seed, "turn_cap": cap,
                   "deadline_s": deadline_s,
                   "hidden_info": bool(getattr(eng, "HIDDEN_INFO", False)),
                   "determinize": hasattr(eng, "determinize")},
        "seats": seats,
        "table_size": table,
        "ladder": ladder,
        "moves": moves,
        "sensitivity": sensitivity,
        "elapsed_s": round(time.monotonic() - started, 1),
        "hit_deadline": time.monotonic() > deadline,
    }


def run_sensitivity(eng, n_players: int, games: int, cap: int, seed: int,
                    deadline: float, policy) -> list:
    """Play each declared assumption both ways and see whether it mattered.

    This is the only cheap way to rank an ambiguity. A rules gap that changes
    nothing measurable can be left for the editor; one that moves the seat bias
    is the game, and the rules have to say which reading is meant.
    """
    assumptions = list(getattr(eng, "ASSUMPTIONS", []) or [])
    if not assumptions:
        return []
    choices = getattr(eng, "CHOICES", None)
    if not isinstance(choices, dict):
        return [{"id": a.get("id", "?"), "rule": a.get("rule", "?"),
                 "verdict": "unwired",
                 "note": "engine declares ASSUMPTIONS but has no CHOICES dict, "
                         "so neither reading can be played"} for a in assumptions]

    def headline(batch: dict) -> dict:
        return {"seat_edge": seat_edge(batch, n_players)["edge"],
                "forced_fraction": batch["forced_fraction"],
                "runaway": batch["runaway"] if batch["runaway"] is not None else 0.0,
                "turns_mean": batch["turns_mean"]}

    base_batch = run_batch(eng, lambda s, g: policy, n_players, games, cap,
                           seed, deadline)
    base = headline(base_batch)
    out = []
    for entry in assumptions:
        aid = entry.get("id", "?")
        was = choices.get(aid, "chosen")
        choices[aid] = "alternative" if was != "alternative" else "chosen"
        try:
            flipped_batch = run_batch(eng, lambda s, g: policy, n_players,
                                      games, cap, seed, deadline)
        finally:
            choices[aid] = was
        flipped = headline(flipped_batch)
        deltas = {
            k: abs(flipped[k] - base[k]) if k != "turns_mean"
            else (abs(flipped[k] - base[k]) / max(base[k], 1.0))
            for k in base
        }
        worst = max(deltas.values()) if deltas else 0.0
        identical = flipped_batch["wins"] == base_batch["wins"] and \
            flipped_batch["turns_mean"] == base_batch["turns_mean"]
        out.append({
            "id": aid, "rule": entry.get("rule", "?"),
            "question": entry.get("question", ""),
            "chosen": entry.get("chosen", ""),
            "alternative": entry.get("alternative", ""),
            "deltas": {k: round(v, 4) for k, v in deltas.items()},
            "worst_delta": round(worst, 4),
            "verdict": ("unwired" if identical else
                        "blocking" if worst > SENSITIVITY_DELTA else "cosmetic"),
        })
    return out


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------

def check(stats: dict) -> list:
    """Thresholds against one `analyse()` result. Pure, so it can be tested
    against synthetic numbers as well as against real playouts."""
    findings: list[str] = []
    table = str(stats.get("table_size"))
    seats = stats.get("seats") or {}
    if not seats:
        return ["playtest: no batches ran at all"]

    # Whether the rules held together long enough for anything else to mean
    # anything. Measured first, because it decides what gets reported at all:
    # a seat-bias number read off the third of games that did not fall down a
    # hole in the rules describes a different game from the one on the page.
    worst_gap, gap_at = 0.0, ""
    for n, pair in seats.items():
        for label in ("random", "greedy"):
            batch = pair[label]
            played = max(batch["games_played"], 1)
            share = (batch["undefined_count"] + batch["stuck"]
                     + (played - batch["natural_endings"] - batch["stuck"]
                        - batch["undefined_count"])) / played
            if share > worst_gap:
                worst_gap, gap_at = share, f"{n}p/{label}"
    unmeasurable = worst_gap > MAX_UNDEFINED_SHARE

    for n, batch_pair in sorted(seats.items()):
        for label in ("random", "greedy"):
            batch = batch_pair[label]
            played = batch["games_played"]
            if batch["undefined_count"]:
                findings.append(
                    f"undefined:{n}p/{label}: the rules ran out during play in "
                    f"{batch['undefined_count']}/{played} games: "
                    + "; ".join(batch["undefined"][:2]))
            if batch["stuck"]:
                findings.append(
                    f"deadlock:{n}p/{label}: {batch['stuck']}/{played} games "
                    f"reached a position with no legal move and no ending, so "
                    f"the rules never say what a stuck player does")
            unfinished = played - batch["natural_endings"] - batch["stuck"] \
                - batch["undefined_count"]
            if unfinished > 0:
                findings.append(
                    f"termination:{n}p/{label}: {unfinished}/{played} games hit "
                    f"the {stats['config']['turn_cap']}-turn cap without ending")

        if unmeasurable:
            continue

        greedy = batch_pair["greedy"]
        if greedy["forced_fraction"] > MAX_FORCED_FRACTION:
            findings.append(
                f"decisions:{n}p: {greedy['forced_fraction']:.0%} of turns offer "
                f"exactly one legal move, over the {MAX_FORCED_FRACTION:.0%} "
                f"where a turn stops being a decision")
        if greedy["branching_median"] < MIN_MEDIAN_BRANCHING and \
                greedy["branching_median"] > 0:
            findings.append(
                f"decisions:{n}p: the median turn offers "
                f"{greedy['branching_median']:.1f} legal moves, under "
                f"{MIN_MEDIAN_BRANCHING:.0f}")

        for label in ("random", "greedy"):
            edge = batch_pair[label]["seat"]
            if edge["edge"] > MAX_SEAT_EDGE:
                findings.append(
                    f"seat:{n}p/{label}: seat {edge['best_seat']} wins "
                    f"{edge['best_rate']:.0%} of decided games against a fair "
                    f"share of {edge['fair_share']:.0%} (95% CI "
                    f"{edge['best_ci'][0]:.0%}-{edge['best_ci'][1]:.0%}), which "
                    f"is the seat playing rather than the player")

        tie_rate = batch_pair["greedy"]["tie_rate"]
        if tie_rate > MAX_TIE_RATE:
            findings.append(
                f"tie:{n}p: {tie_rate:.0%} of finished games end level, so the "
                f"tiebreaker in rules:win is not breaking ties")

        runaway = batch_pair["greedy"]["runaway"]
        if runaway is not None and runaway > MAX_RUNAWAY:
            findings.append(
                f"runaway:{n}p: whoever leads at the halfway point goes on to "
                f"win {runaway:.0%} of the time, so the second half is a "
                f"formality")

    if unmeasurable:
        findings.append(
            f"unmeasurable: {worst_gap:.0%} of games at {gap_at} ended in a "
            f"rules gap rather than at the win condition, so the only games "
            f"left to measure are the subset the rules happened to cover. "
            f"Every seat, tie, runaway, depth, length and dead-move check is "
            f"suppressed until the gaps above are closed. Nothing here says "
            f"the game is bad; it says the game has not been played yet")
        return findings

    # `first` is excluded on purpose: it beats random whenever the engine
    # happens to enumerate good moves early, which measures the engine's list
    # order, not the game. It is reported for exactly that reason.
    ladder = [r for r in (stats.get("ladder") or [])
              if r["games"] >= MIN_LADDER_GAMES]
    thin = [r for r in (stats.get("ladder") or [])
            if r["games"] < MIN_LADDER_GAMES]
    if thin:
        findings.append(
            "sample: " + ", ".join(f"{r['policy']} vs {r['field']} n={r['games']}"
                                   for r in thin)
            + f" finished fewer than {MIN_LADDER_GAMES} games, so those rungs "
              f"are reported and then ignored by the depth check")
    skilled = [r for r in ladder
               if r["field"] == "random" and r["policy"] in ("greedy", "lookahead")]
    best = max((r["edge"] for r in skilled), default=0.0)
    if stats["config"]["hidden_info"] and not stats["config"]["determinize"]:
        findings.append(
            "depth_unmeasured: the game has hidden information and the engine "
            "has no determinize(), so the lookahead policy played with the "
            "face-down pieces visible. Its win rate is an upper bound on what a "
            "player could reach, not a measurement of skill, and the depth "
            "check below is reading the wrong number")

    if skilled and best < MIN_SKILL_EDGE:
        rungs = ", ".join(f"{r['policy']} {r['win_rate']:.0%}"
                          for r in ladder if r["field"] == "random")
        findings.append(
            f"depth: no policy beats random play by more than {best:+.0%} above "
            f"its fair share ({rungs}); looking a whole game ahead buys nothing, "
            f"so there is nothing here to be good at")

    # Two ways the ladder above can be measuring the harness instead of the
    # game. Neither is a verdict on the game, and both make every number in
    # the depth row mean less than it looks like it means.
    ordering = next((r for r in ladder if r["policy"] == "first"), None)
    if ordering and ordering["edge"] > MIN_SKILL_EDGE:
        findings.append(
            f"ordering: taking whatever the engine lists first beats random by "
            f"{ordering['edge']:+.0%} above fair share, so the engine enumerates "
            f"good moves early and the random baseline is a weak opponent. "
            f"Every edge over random above is inflated by this much")

    one_ply = next((r for r in ladder
                      if r["policy"] == "greedy" and r["field"] == "random"), None)
    if one_ply and one_ply["ci"][1] < one_ply["fair_share"]:
        findings.append(
            f"proxy: the greedy policy loses to random play "
            f"({one_ply['win_rate']:.0%} against a fair share of "
            f"{one_ply['fair_share']:.0%}), so maximising scores() one ply "
            f"ahead is actively bad here and the all-greedy baseline every "
            f"seat, tie, runaway and length number is read from describes a "
            f"table of players worse than dice")

    turns = seats[table]["greedy"]["turns_mean"]
    claimed = stats["idea"]["playtime_min"]
    if claimed and turns:
        fast, slow = SECONDS_PER_DECISION
        quick, drawn = turns * fast / 60.0, turns * slow / 60.0
        floor, ceiling = LENGTH_TOLERANCE
        if not (quick * floor <= claimed <= drawn * ceiling):
            findings.append(
                f"length: {turns:.0f} decisions at {table} players is "
                f"{quick:.0f} to {drawn:.0f} minutes at {fast:.0f}-{slow:.0f}s a "
                f"turn, and no plausible pace reaches the claimed playtime_min "
                f"of {claimed}")

    moves = stats.get("moves") or {}
    for kind in moves.get("never_legal", []):
        findings.append(
            f"dead_move:{kind}: the rules define this action and it was never "
            f"once legal in any game, so no player can ever take it")
    for kind in moves.get("never_chosen", []):
        findings.append(
            f"dead_move:{kind}: legal, and never once chosen across every game "
            f"where all seats played to win, so it is an option nobody wants")

    for entry in stats.get("sensitivity") or []:
        if entry["verdict"] == "blocking":
            findings.append(
                f"ambiguous:{entry['rule']}: {entry['question']} The rules do "
                f"not say, and playing it the other way moves the numbers by "
                f"{entry['worst_delta']:.0%}, so this reading IS the game")
        elif entry["verdict"] == "unwired":
            findings.append(
                f"contract:{entry['id']}: declared as an assumption but the "
                f"engine plays identically both ways, so the flip is not wired "
                f"to anything and the ambiguity was never tested")

    if stats.get("hit_deadline"):
        findings.append(
            "budget: the run hit its wall-clock deadline, so some batches are "
            "short of their requested game count and every interval above is "
            "wider than it reads")

    return findings


# A bare FAIL is not enough to act on. "The rules ran out" and "the first seat
# always wins" are both failures and they go to different places: one is a
# sentence somebody forgot to write, one is a design that does not work. The
# class is what a caller routes on; the findings are what gets fixed.
CATEGORY = {
    # The rules do not describe a whole game yet. Somebody has to write a
    # sentence that is missing.
    "undefined": "rules_incomplete", "deadlock": "rules_incomplete",
    "termination": "rules_incomplete", "unmeasurable": "rules_incomplete",
    # The rules describe two games and do not say which. Measured to matter.
    "ambiguous": "rules_ambiguous",
    # Something other than play is deciding the outcome. Needs a redesign,
    # not an edit.
    "seat": "not_a_game", "depth": "not_a_game", "decisions": "not_a_game",
    "runaway": "not_a_game",
    # Real defects that a rules edit fixes without touching the design.
    "tie": "rough_edges", "dead_move": "rough_edges", "length": "rough_edges",
    # Nothing about the game. The harness or the engine warning about itself.
    "ordering": "measurement", "proxy": "measurement",
    "depth_unmeasured": "measurement", "contract": "measurement",
    "sample": "measurement", "budget": "measurement", "playtest": "measurement",
}

# Most severe first. `rules_incomplete` outranks everything because until the
# rules describe a whole game there is nothing to have an opinion about, and
# every other measurement is suppressed anyway.
SEVERITY = ["rules_incomplete", "not_a_game", "rules_ambiguous",
            "rough_edges", "measurement"]


def classify(findings: list) -> tuple[str, dict]:
    counts: dict[str, int] = {}
    for finding in findings:
        prefix = finding.split(":", 1)[0].strip()
        cls = CATEGORY.get(prefix, "measurement")
        counts[cls] = counts.get(cls, 0) + 1
    for cls in SEVERITY:
        if counts.get(cls):
            return cls, counts
    return "clean", counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def summarise(stats: dict) -> str:
    lines = []
    table = str(stats["table_size"])
    for n, pair in sorted(stats["seats"].items()):
        g = pair["greedy"]
        edge = g["seat"]
        lines.append(
            f"  {n}p  {g['natural_endings']}/{g['games_played']} finished, "
            f"{g['turns_mean']:.0f} turns, {g['branching_median']:.1f} moves/turn "
            f"({g['forced_fraction']:.0%} forced), best seat "
            f"{edge['best_rate']:.0%} vs {edge['fair_share']:.0%} fair")
    lines.append(f"  ladder at {table}p (win rate, fair share "
                 f"{1 / int(table):.0%}):")
    for rung in stats["ladder"]:
        lines.append(f"    {rung['policy']:>9} vs {rung['field']:<7} "
                     f"{rung['win_rate']:.0%}  CI "
                     f"{rung['ci'][0]:.0%}-{rung['ci'][1]:.0%}  n={rung['games']}")
    for entry in stats.get("sensitivity") or []:
        lines.append(f"  assumption {entry['id']}: {entry['verdict']} "
                     f"(worst delta {entry['worst_delta']:.0%})")
    if stats["config"]["hidden_info"]:
        lines.append("  hidden information: "
                     + ("resampled per decision"
                        if stats["config"]["determinize"]
                        else "NOT modelled, the lookahead rung is an oracle"))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("idea_dir", type=Path,
                    help="board-game/ideas/<slug> (or its idea.json)")
    ap.add_argument("--engine", type=Path,
                    help="default <idea dir>/playtest/engine.py")
    ap.add_argument("--out", type=Path, help="default <idea dir>/playtest.json")
    ap.add_argument("--games", type=int, default=DEFAULT_GAMES)
    ap.add_argument("--ladder-games", type=int, default=DEFAULT_LADDER_GAMES)
    ap.add_argument("--mc-budget", type=int, default=DEFAULT_MC_BUDGET)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--deadline", type=float, default=DEFAULT_DEADLINE)
    ap.add_argument("--quick", action="store_true",
                    help="a few games of everything, to prove the engine runs")
    ap.add_argument("--report-only", action="store_true",
                    help="shadow mode: print the verdict, always exit 0")
    args = ap.parse_args()

    idea_dir = args.idea_dir.parent if args.idea_dir.is_file() else args.idea_dir
    idea_path = idea_dir / "idea.json"
    if not idea_path.is_file():
        print(f"PLAYTEST ERROR no idea.json at {idea_path}")
        return 2
    idea = json.loads(idea_path.read_text(encoding="utf-8"))
    engine_path = args.engine or (idea_dir / "playtest" / "engine.py")
    if not engine_path.is_file():
        print(f"PLAYTEST ERROR no engine at {engine_path} — "
              f"board-game-rules-engineer writes it")
        return 2

    games = 20 if args.quick else args.games
    ladder_games = 8 if args.quick else args.ladder_games
    mc_budget = 20 if args.quick else args.mc_budget

    try:
        eng = load_engine(engine_path)
        contract = validate_engine(eng)
        if contract:
            print(f"PLAYTEST ERROR engine does not satisfy the contract")
            for finding in contract:
                print("  -", finding)
            return 2
        stats = analyse(eng, idea, games=games, ladder_games=ladder_games,
                        mc_budget=mc_budget, seed=args.seed,
                        deadline_s=args.deadline)
    except EngineBroken as exc:
        print(f"PLAYTEST ERROR {exc}")
        return 2

    findings = check(stats)
    verdict, counts = classify(findings)
    report = {"idea": str(idea_path), "engine": str(engine_path),
              "pass": not findings, "verdict": verdict, "by_class": counts,
              "findings": findings, "stats": stats}
    out = args.out or (idea_dir / "playtest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(("PLAYTEST PASS " if report["pass"] else f"PLAYTEST FAIL {verdict} ")
          + f"{len(findings)} finding(s) in {stats['elapsed_s']}s")
    print(summarise(stats))
    for finding in findings:
        print("  -", finding)
    return 0 if (report["pass"] or args.report_only) else 1


if __name__ == "__main__":
    sys.exit(main())
