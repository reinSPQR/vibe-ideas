# CAD GRAMMAR — what this text-to-CAD pipeline actually preserves

The empirical record of which physical feature classes survive a build, which
are lost but recoverable by a repair round, and which never survive at all.

This is the durable product of the `/goal` loop. Scores are rubric-specific
and expire; this table does not. It is written by `board-game-evaluator`
after each turn, read by `board-game-ideator` (design around what is LOST)
and `board-game-cad-writer` (state explicitly what is fragile), and it is the
one artifact that stays useful across rubric changes.

Rules for maintaining it:

- Rows are **feature classes**, never specific ideas. "48 loose tiles of one
  shape, 2 mm gap in layout" generalizes; "Foghorn's suit tiles" does not.
- Update an existing row rather than adding a near-duplicate class.
- When later evidence contradicts an earlier verdict, say so in the row
  instead of overwriting — a class that survives sometimes is a different
  and more useful fact than a class that always does.
- Verdicts: `PRESERVED` · `LOST first shot, RECOVERED by repair` ·
  `LOST — never recovers` · `UNTESTED`.

| Feature class | Verdict | Evidence |
|---------------|---------|----------|
| 40+ loose same-shape pieces laid out adjacent to a board | LOST — fused into one continuous mat | t13 (48 numbered suit tiles) |
| disc intended to rotate on a printed pin/plaque | LOST — fused into one static body | t13 (trump dial + base plaque) |
| a specified container/tray listed in components | LOST — absent from the build entirely | t13 (trick collection tray) |
| fine engraved traces + small raised nodes on a single plate | LOST — surfaced as a plain closed box, zero relief | t12 (circuit-board plate) |
| 4 part types × 4 colour groups, ~65 pieces | LOST — collapsed to one solid with the grid merely engraved into its lid | t11 (cargo grid) |
| flat engraved tiles, static peg tracks, no joints | PRESERVED | t9, t13 (player racks, box, lid printed as correct distinct pieces) |

**Standing note on printability:** a fused, featureless solid is trivially
printable and has scored 8.97/10 while destroying the design. A high
printability score next to a failed component count is not a contradiction —
it is the fusion signature. Never read printability as reassurance on its own.

**Standing note on parks:** across turns 11-13, 5 of 9 builds never finished,
and the "safe on paper" ideas parked at the same rate as everything else.
Under the old loop a park scored zero and its question text was discarded.
It is now answered and logged — see `CAD_QUESTIONS.md`.
