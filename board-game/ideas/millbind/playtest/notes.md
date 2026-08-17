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

The bind test (`rules:turn[5]`) is implemented as a literal whole-graph
odd-cycle check: build the mesh graph from every occupied pin and its
lattice-adjacent occupied neighbours where tooth tiers are compatible
(`gear_low`-`gear_low`, `gear_high`-`gear_high`, or either side full-height),
then 2-colour every connected component by BFS. A colour clash anywhere is an
odd cycle, i.e. bound — checked against a hand-built triangle (binds), a
hand-built even 4-node subgraph that turned out to contain a chord and hence
a triangle (correctly binds), the full 18-pin outer ring as a plain even
cycle (does not bind), and that same ring plus one inner pin that chords two
adjacent yard pins into a triangle (correctly binds) — see the scratch
checks run before writing these notes, not part of the shipped engine.

Direction (`rules:turn[8]`) falls straight out of the same 2-colouring: a
millstone scores clockwise iff it is in the crank's connected component and
shares the crank's colour. This is exact, not an approximation — in a
bipartite graph every path between two nodes has the same parity, so "the
chain that connects them" is well defined regardless of which of several
possible paths you'd trace by hand.

Millstone/crank placement during setup (`rules:setup[3..4]`) is modelled as
real moves (`setup_mill`, `setup_crank`), not baked into `new_game`, because
"any empty yard pin" is a real strategic choice in the rules text, not
scaffolding.

Scores are the literal sack_spindle pellet counts, valid at every point in
the game, no proxy needed.

`HIDDEN_INFO = False`: the yard, the supply pile and every score are visible
to all seats at all times. No `determinize` needed.

## Undefined — two genuine gaps, not bugs

**1. `rules:turn[7]` — the crank can jam itself with no rule to catch it.**
`rules:turn[1]` POWER lets the start player move the crank_gear to *any*
empty yard pin, with no bind test at all. `rules:turn[5]` TEST FOR A BIND is
scoped explicitly to "Immediately after a PLACE or a SHIFT" — POWER isn't
named. But moving the crank changes every mesh edge incident to its new pin,
and can close an odd loop through its own cluster exactly the way a PLACE or
SHIFT can (the triangular lattice is full of potential triangles once the 19
inner pins start filling with supply gears). When that happens, every
PLACE/SHIFT attempted for the rest of the round finds the whole graph already
bound and reverts (nothing can un-bind a graph by adding edges to it), and
`rules:turn[7]` THE GRIND — which assumes the crank always completes one full
clockwise turn — has nothing to say about a crank that cannot physically turn
at all. The engine raises `Undefined` at that point rather than guessing
whether POWER should have been bind-tested too, whether the round grinds
nothing, or something else.

This is not a rare edge case: in the `--quick` run (20 games/policy, small
board fill) it fired in roughly a third to nearly all games depending on
seat count and policy (9/20 at 2p/random, 17/20 at 4p/random). A human
table would almost certainly catch this by feel — whoever holds the crank
knob would notice it won't turn — but the written rule never says so, and a
strict reading of the text leaves POWER's bind test genuinely missing. This
is the single most important finding from writing this engine and belongs
back with the rules, not patched here.

**2. `rules:turn[7]` / `rules:end[1]` — a granary that runs out mid-payout.**
THE GRIND owes one grain_pellet per clockwise millstone, two instead of one
if exactly one turned. `rules:end[1]` ends the game "at the end of the round
in which the granary_bin is emptied", which only cleanly covers a payout
that exactly exhausts the bin. Nothing says what happens if a round's payout
(up to 4 pellets, or 2 for a single scorer) needs more than the granary has
left — pay a partial amount, pay some millstones and not others, or something
else. The engine raises `Undefined` when this is actually reached rather
than inventing a rationing rule.

Both are left exactly as the rules leave them: not repaired, not smoothed
over, not routed around by making the "obviously intended" choice, per the
rule of this stage.

## Assumptions

None declared. Every other place the rules could be read two ways resolved
to a single plain reading on inspection:

- PLACE's "any empty pin, yard pin or inner" (`rules:turn[3]`) explicitly
  lets supply gears stand on yard pins too; `rules:setup[0]`'s "the only
  pins a millstone or crank_gear may ever stand on" restricts mills/crank to
  yard pins, it doesn't reserve yard pins for them exclusively. Not
  ambiguous, just easy to misread on a skim — implemented as PLACE having
  the run of all 37 pins.
- "nudge one gear in every separate cluster the crank cannot reach"
  (`rules:turn[5]`) is explicit that the bind test covers every connected
  component of the mesh graph, not only the crank's own — implemented as a
  whole-graph check, not a crank-reachability-limited one.
- PASS being freely choosable rather than only a forced fallback
  ("A player with no legal action must pass" reads as a corollary of the
  free choice, not a restriction on it) — implemented as always legal.
- A PLACE/SHIFT that would bind is modelled as attempted-then-reverted
  (per the literal "take the piece back ... your turn ends with nothing
  done" text), not filtered out of `legal_moves` in advance. The two are
  provably equivalent in resulting board state for a rational policy — the
  only place this could show up is in the random baseline's move
  distribution — so this was a straightforward reading of the text, not a
  50/50 fork worth spending an `ASSUMPTIONS` entry on.

I looked specifically for a genuine "both readings let play continue"
ambiguity to exercise the sensitivity machinery and did not find one worth
declaring; inventing one to have something to flip would be the same sin as
picking the reading that makes the game work.

## `--quick` run

```
.venv/bin/python board-game/tools/playtest.py board-game/ideas/millbind --quick
```

Reached a verdict line (`PLAYTEST FAIL 7 finding(s)`), not `PLAYTEST ERROR`
— the engine runs. All six declared `MOVE_KINDS` were both legal and chosen
at least once in the sample. The FAIL itself is expected and uninformative
at `--quick` scale (20 games, 8 ladder games) with the crank-jam gap firing
constantly enough to starve every batch of finished games; the real verdict
is for the full gate to render, not this stage.
