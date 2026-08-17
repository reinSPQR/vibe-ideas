# Millbind — engine notes

## Model

37 pins as hex/cube coordinates `(q, r, s=-q-r)`, `ring = max(|q|,|r|,|s|)`.
The six standard axial neighbour offsets are exactly the six nearest-neighbour
directions of a triangular lattice at unit spacing, so "hex distance 1" and
"physically 30mm apart, teeth able to touch" are the same relation — no
Cartesian coordinates were needed. `ring <= 2` (19 pins) are inner pins,
`ring == 3` (18 pins) are yard pins. Verified: 37 pins total, 19 inner + 18
yard, centre has 6 neighbours, yard pins have degree 3 (the 6 hexagon
corners) or 4 (the 12 edge pins) — the shape a hexagonal chunk of triangular
lattice should have.

The bind test is a literal whole-graph odd-cycle check: build the mesh graph
from every occupied pin and its lattice-adjacent occupied neighbours where
tooth tiers are compatible (`gear_low`-`gear_low`, `gear_high`-`gear_high`, or
either side full-height), then 2-colour every connected component by BFS. A
colour clash anywhere is an odd cycle, i.e. bound. Direction falls straight
out of the same 2-colouring: a millstone scores clockwise iff it is in the
crank's connected component and shares the crank's colour — exact, not an
approximation, because in a bipartite graph every path between two nodes has
the same parity.

Millstone/crank placement during setup is modelled as real moves
(`setup_mill`, `setup_crank`), not baked into `new_game`, because "any empty
yard pin" is a real strategic choice in the rules text, not scaffolding.

Scores are the literal sack_spindle pellet counts, valid at every point in
the game, no proxy needed.

`HIDDEN_INFO = False`: the yard, the supply pile and every score are visible
to all seats at all times. No `determinize` needed.

## This pass: both blocking gaps closed by the rework, engine updated to match

`rules_check.py` and `board-game-lens-rules` both signed off on the reworked
five steps in `idea.json`; this pass is the part that proves they run. Both
findings from `review_playtest.md` trace to text that changed and are now
implemented, not raised:

**1. `rules:turn[1]` POWER is now bind-tested before the crank commits.**
`legal_moves` at `phase == "power"` builds the candidate list by running the
whole-graph bind test on a *hypothetical* layout for each empty yard pin —
the crank's old pin cleared, the candidate pin holding the crank — and only
offers pins that pass. `("power", state["crank_pin"])` (staying put) is
always included unconditionally, matching "leaving the crank on its own pin
is always legal and always turns" — that pin was proven non-binding at the
end of the previous round (THE GRIND only completes from an unbound yard),
and staying changes no mesh edge, so it never needs testing. Because POWER
"is not one of the three actions" and retries are free and unlimited, a
binding candidate is simply not offered rather than being attempted and then
reverted — that is the behavioural difference from PLACE/SHIFT, which still
cost the action on a bind (`apply_move`'s "place"/"shift" branches, unchanged
from before this pass).

**2. `rules:turn[5]` TEST FOR A BIND is rescoped, and the engine's three call
sites now match it.** PLACE/SHIFT keep test-then-revert in `apply_move`
(unchanged). POWER moved from "no test at all" to the pre-commit filter in
(1) — same underlying `_build_adj`/`_analyze_graph` machinery, invoked
through a new `_would_bind(pins, overrides)` helper that copies the pins dict
rather than mutating game state, since `legal_moves` must not mutate.

**3. `rules:setup[4]` setup is bind-tested but provably cannot fail, so the
engine asserts the geometry instead of testing it.** The rework states setup
"cannot fail here" and gives the reason: the 18 yard pins form a single ring.
I did not add a test-then-revert path to `setup_mill`/`setup_crank` — I
resolved the "is this reachable" question the same way the rework's own text
does, by proof rather than by trial: the 18 yard pins form exactly one
18-cycle (verified in `NEIGHBORS`/`EDGES` at module load — every yard pin has
exactly two yard-pin neighbours), a cycle graph is bipartite, and during
setup only full-height pieces (millstones, then the crank) ever stand on yard
pins — no supply gear exists yet to add a chord across the ring. Every
possible setup mesh graph is therefore a subgraph of one bipartite cycle and
provably 2-colourable, i.e. never bound, regardless of how many of the up-to-
five full-height pieces are standing. Writing a test-then-revert branch that
a thousand games could never exercise would be dead code pretending to be a
rule; instead `apply_move`'s `setup_mill`/`setup_crank` branches carry an
`assert not _is_bound_state(state)` — a mechanical check of the proof, cheap
at this piece count, that would fail loudly (as an engine bug, not an
`Undefined`) if the geometry claim were ever wrong. It did not fire in any
run, including the full gate below.

**4. `rules:turn[7]` THE GRIND's bound branch is now an assertion, not an
`Undefined`.** With POWER pre-filtered and PLACE/SHIFT still tested-then-
reverted, no move that reaches `_process_grind` can have left the yard bound
— every path that could bind it either never offers the binding option
(POWER) or reverts it immediately (PLACE/SHIFT). rules:turn[7]'s own
recovery clause ("undo this round's moves ... until it turns") exists for a
human table that skipped a physical test, which cannot happen in this engine
by construction. So a bound yard reaching THE GRIND now raises
`AssertionError`, not `Undefined`: it would mean an engine defect, not a
remaining rules gap, and conflating the two would hide a bug behind the same
signal that's supposed to mean "the rules don't say." Did not fire in the
full gate run below.

**5. `rules:turn[8]` A SHORT GRANARY (new step) replaces the old `need >
pellets` `Undefined`.** `_process_grind` now computes each clockwise
millstone's debt (1 pellet, or 2 for a lone scorer), then pays pellets out
one at a time in clockwise order starting from the round's start player
(`state["action_order"]`, already built that way), repeating full passes
until every debt clears or the bin empties. Verified against both worked
examples in the rule text: two mills owed 1 each with 1 pellet left pays only
the earlier one in clockwise order; a lone mill owed 2 with 1 pellet left
scores 1 (not 0, not 2). When the bin fully covers the round's debts this is
behaviourally identical to the old flat subtraction — same total paid, same
recipients — so no measurable change on any game that wasn't hitting the old
`Undefined`.

**6. `rules:end[1]`** — "the round in which the last grain_pellet leaves the
granary_bin, whether that grind paid every mill in full or ran the bin dry
part-way through" is exactly the existing end condition
(`state["pellets"] == 0`), which needed no code change; only the comment
citing it was checked against the new wording.

**Citation hygiene.** `turn` is now 11 steps (0-10): THE GRIND stays
`rules:turn[7]` (unchanged index — the new step was inserted after it), A
SHORT GRANARY is the new `rules:turn[8]`, DIRECTION moved from `rules:turn[8]`
to `rules:turn[9]`, and the closing "pass the start player role" step moved to
`rules:turn[10]`. All in-code citations were checked against these new
indices, not carried over from the pre-rework text.

## No new `Undefined`, no new `ASSUMPTIONS`

Both declared gaps from the previous pass are gone — not smoothed over, the
rules that created them changed and the engine now implements the answer the
new text gives. I looked specifically for a new "both readings let play
continue" ambiguity introduced by the rework and did not find one:

- POWER's retry language ("you may keep trying pins, nothing is spent") is
  behaviourally equivalent to filtering the candidate list up front, since
  nothing about the outcome differs and no cost attaches either way — not a
  fork worth an `ASSUMPTIONS` entry.
- A SHORT GRANARY's ordering ("beginning with the start player and going
  clockwise ... to each owner still owed") is unambiguous and was implemented
  literally.
- Setup's "cannot fail here" is a claim I verified rather than an
  instruction I had to guess at.

`ASSUMPTIONS = []` and `CHOICES = {}` remain empty, same as before this pass,
for the same reason: inventing a fork to exercise the sensitivity machinery
would be the same sin as picking the reading that makes the game work.

## `--quick` run

```
.venv/bin/python board-game/tools/playtest.py board-game/ideas/millbind --quick
```

Reaches a verdict line (`PLAYTEST FAIL measurement 1 finding(s)`), not
`PLAYTEST ERROR` and not `rules_incomplete` — no `Undefined` fired anywhere
in the sample. The one finding at `--quick` scale is a measurement-depth
warning (several ladder rungs short of `MIN_LADDER_GAMES` at only 8 games
each), which is expected and uninformative at this sample size; the full run
below is the real signal.

## Full gate (`--games 300 --ladder-games 60 --mc-budget 40 --seed 7`)

```
.venv/bin/python board-game/tools/playtest.py board-game/ideas/millbind --games 300 --ladder-games 60 --mc-budget 40 --seed 7
```

`PLAYTEST PASS 0 finding(s)` in 183.2s. `playtest.json`: `pass: true`,
`verdict: clean`, `findings: []`.

| batch | played | undefined | natural endings |
|---|---|---|---|
| 2p random | 300 | 0 (0%) | 300 |
| 2p competent (greedy) | 300 | 0 (0%) | 300 |
| 4p random | 300 | 0 (0%) | 300 |
| 4p competent (greedy) | 300 | 0 (0%) | 300 |

Pre-rework baseline for comparison: 2p random 167/300 (56%), 2p greedy
123/300 (41%), 4p random 255/300 (85%), 4p greedy 248/300 (83%). All four
cells go from double-digit-percent undefined to exactly zero.

Skill ladder: **240/240 requested games completed** (60 at each of 4 rungs —
first-vs-random, greedy-vs-random, lookahead-vs-random, lookahead-vs-greedy),
versus 16/240 pre-rework. `elapsed_s: 183.2`, `hit_deadline: false`. All six
`MOVE_KINDS` both legal and chosen at least once (`moves.never_legal: []`,
`moves.never_chosen: []`).

Ladder results (fair share 25% at 4p): first vs random 14.6% (edge -0.17),
greedy vs random 56.1% (edge +0.19), lookahead vs random 46.3% (edge +0.10),
lookahead vs greedy 30.0% (edge -0.05). Not a verdict on the game — that's the
next stage's job — just confirmation the ladder now runs to completion and
produces a real signal instead of aborting on `Undefined` inside every
policy's own speculative lookahead.

## Patch: `observation(state, seat)` added, no rule logic touched

`HIDDEN_INFO = False`, so nothing is secret — this addition is about
legibility, not concealment. `playtest.observe()` falls back to the raw
internal state dict when an engine has no `observation()`, and a table run on
`board-game/ideas/millbind/playtest/table/probe1.json` (turn 5, seat 1) showed
that raw dict defeats a model seated there: it cannot tell that `crank_pin`
(one coordinate) and `mill_pin` (a per-seat list) are different shapes, it
gets 34 nulls out of 37 entries in `pins`, and nothing anywhere states which
pins neighbour which even though `rules:turn[0]` MESHING and the entire bind
test are written wholly in terms of that adjacency.

`observation()` now returns:

- `phase`, `round`, `to_move`, `start_player`, `game_over`, `crank_pin` —
  same facts as before, `crank_pin` now a formatted pin id instead of a bare
  coordinate.
- `you` — the observing seat's own `mill_pin` and `pellets` pulled forward,
  so the reader never indexes into an array to find its own things; `seats`
  carries the same for every seat (all public, `HIDDEN_INFO = False`).
- `supply`, `granary_pellets_remaining`, `gear_placed_this_round`,
  `last_grind_clockwise_seats` — same underlying facts, renamed to the
  rulebook's own nouns (`granary_bin`, `grain_pellet`) rather than the
  engine's internal field names.
- `board.yard_pins` / `board.inner_pins` — the `rules:setup[0]` distinction
  the raised sill marks physically, stated outright rather than left for the
  reader to reconstruct from `ring == 3`.
- `board.edges` — the full 90-edge adjacency of the 37-pin lattice, every
  time. This is the fix for the failure that was actually observed: a player
  at a real table reads which pins touch by hand and eye in a second, and
  withholding it made the model reconstruct a triangular lattice from cube
  coordinates under its own steam, which is a different and harder puzzle
  than Millbind. Pin ids are formatted with plain `str((q, r))`, e.g.
  `"(-1, -2)"`, deliberately matching the substring that already appears
  inside every move tuple in the `LEGAL MOVES` list printed alongside it, so
  a pin can be found by eye rather than translated between two coordinate
  spellings — the mismatched `crank_pin`/`mill_pin`/`pins` shapes were part
  of the original problem.
- `board.pieces` — only occupied pins (an absent id means empty, as an
  absent piece on the physical board does), each with `piece` (the same
  type string `apply_move` uses: `gear_low`/`gear_high`/`gear_tandem`/
  `mill`/`crank`) and `mesh_height` (`"low"`/`"high"`/`"full"`, straight
  from the existing `_tier()` helper) stated outright instead of left for
  the reader to infer from the type string, per `rules:turn[0]`. Millstones
  also carry `owner`.

Left out deliberately: `action_order`/`action_index`/`setup_index`, which
are the engine's own progress pointers through information already present
as `phase`, `to_move` and `start_player` — a player at the table does not
track an index, they watch whose turn it is. Nothing was added beyond what a
seated player already sees on the physical board plus what the rules state
about it: no evaluation, no flag on which moves would bind, no hint.

**Nothing that plays the game reads `observation()`.** All scripted policies
and the lookahead read `state` directly (as they must, to stay fast over
thousands of games), so this patch cannot and does not change any legality,
scoring, or move probability. Confirmed: the full gate
(`--games 300 --ladder-games 60 --mc-budget 40 --seed 7`) still reports
`PLAYTEST PASS 0 finding(s)`, `verdict: clean`, and the ladder numbers match
the pre-patch run within seed noise (first vs random 15% vs 14.6%, greedy vs
random 56% vs 56.1%, lookahead vs random 46% vs 46.3%, lookahead vs greedy
30% vs 30.0%). `HIDDEN_INFO = False` means `observation_leaks()` returns `[]`
immediately without needing a `determinize()` — confirmed still `leaks: []`
in `playtest.json`.

Size, on `probe1.json` (turn 5, seat 1): the old raw-state block (observation
+ the 114-move list) was 5651 chars. The new observation alone is bigger in
isolation — 2977 chars compact, because it now carries the full board
topology that the old dump omitted entirely — but that topology is exactly
the thing the transcript shows a model needed and didn't have. The full
table block (new observation + unchanged move list) is 7226 chars compact.
Not a compression exercise: the goal was a reader who has the rulebook and
not the code being able to act on the position, not a byte count.
