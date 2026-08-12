# Sellability Scores — Turn 14

Rubric: Vision Fidelity/60 + Build Reliability/25 + Vision Ambition/15 = /100.
Only the first-shot build is scored for Fidelity; Reliability is 0 whenever
the first shot didn't reach `done`. See `board-game/AMBITION.json` for the
locked pre-build Ambition scores.

## Summary

| # | Title | Path | Ambition /15 | Fidelity /60 | Reliability /25 | Total /100 | Build status | Counted? |
|---|-------|------|---------------:|----------------:|--------------------:|-------------:|---------------|----------|
| 1 | Keyhold | new | 13 | 0 | 0 | 13 | **failed** (llm_error, plan-generation) | no |
| 2 | Twin Deck Solitaire | twist | 12 | 48.0 | 20.68 | 80.68 | done | **yes** |
| 3 | Eclipse | reskin | 9 | 0 | 0 | 9 | **failed** (worker_error, concept-phase) | no |

**Average (counted ideas): 80.68 / 100** (idea 2 only)
**First-shot must_survive survival: 80%** (idea 2 only; 27% across all 3 ideas including the two that never reached a build)

All three ideas pass the novelty gate (one confirming search each, none
contradicted). Ideas 1 and 3 are excluded from the average not for novelty
or low ambition — both score above the 8/15 floor — but because neither
ever produced a build artifact: idea 1's CAD job returned `llm_error`
("couldn't produce a plan") seconds after concept selection, and idea 3's
concept-phase worker died with `worker_error` ("response exceeded the
32000 output token maximum") ~35 minutes into round-2 style generation.
Neither failure was a park requiring a design decision, and neither has any
geometry, render, or session artifact beyond the terminal failure event —
there is nothing to measure Fidelity or Reliability against, so both total
their Ambition score alone and that total is not comparable to idea 2's
real build outcome.

## Per-idea notes

**1. Keyhold (13/100, not counted).** Ambition 13/15 — genuinely the
strongest concept of the batch on paper: ownership encoded purely in
mating tooth geometry (1-tooth vs. 2-tooth families) on a real stepped 7x7
pedestal waffle, with a tight 0.4mm fit tolerance putting actual interlock
risk on the table. None of that was ever tested: `session.json` shows
`submit` → `parked` (`awaiting_concept_selection`) → `select_concept` →
**`terminal: failed`** in under 4 minutes total, with no plan, no question,
no CAD job. This is a pipeline/tooling failure squarely upstream of the
`cad_prompt` quality (which fully covered all 5 `must_survive` ranks per
`CAD_PROMPTS.json`'s own coverage block) — nothing here indicates the spec
itself was the problem.

**2. Twin Deck Solitaire (80.68/100, counted).** The only build to reach
`done` this turn, and the geometry backs up the concept. Of the 5
`must_survive` ranks, only rank 3 (peg separation, 70/70 components) got a
clean geometric `pass` from `score_build.py` — the other 4 (air gap, hole
count, hole alignment, peg/hole fit) all came back `inconclusive`, but this
is a scoring-harness bug, not a build defect: `compile_conditions()` reads
`geometric.get("inputs")`, a key this turn's `IDEAS.json` schema never
populates (it uses `"parts"`/`"thresholds"` instead), so those four checks
are structurally unable to resolve regardless of correctness. Reading
`project/main.py` directly confirms all four are numerically satisfied —
`GAP = 30.0` (threshold 25-35mm), both boards built from the identical
`cross_positions()` call (0.0mm alignment offset against a 1.0mm
threshold), and `PEG_D = 11.4` vs. `HOLE_D = 12.0` (exactly the spec'd
0.3mm radial clearance) — and the ortho renders in `project/main_review/`
(`board_top.png`'s unoccluded top view: 33 clean circular holes in the
correct cross layout; `main_section_x.png`/`main_section_y.png`: peg
columns vertically stacked with no visible lateral offset between layers,
including the one floating peg centered exactly on-axis in the gap;
`assembled.png`/`qa.png`: two boards visibly separated by open air,
connected only by the 4 corner posts) independently confirm every one of
the 5 visual instructions. Per the rubric, the inconclusive geometric
checks still only earn 0.5 credit each (not overridden to 1.0), which is
why `geometric_fidelity` = 0.6 exactly as `evaluation_report.json` reports
it, while `visual_fidelity` = 1.0 and blended `Fidelity` = 48.0/60.
Reliability: 15 base − 2 (one concept-selection question) + 7.68
(independent `printability_0_10`) = 20.68/25. Worth flagging: the
pipeline's own `review_fix.printability` scored a perfect 10 in
"printability-only" mode with 0 iterations, against the independent
scorer's 7.68 (flagging "70 disconnected mesh components" and 10.7%
unsupported overhang) — here the 70 components are the *correct* outcome
(2 boards + 4 posts + 64 loose pegs, matching the expected count exactly),
so this isn't the fusion-signature pattern BOARD.md warns about, just the
pipeline's own grader missing a real multi-body print-planning risk factor
that an assembly this size genuinely carries. One real, unscored deviation:
the `cad_prompt` asked for 15mm-deep blind bores at the post insertion
points; the model instead cut `BORE_D=7.85` clean through both boards'
full 12mm thickness, so each post's insertion pin pokes ~3mm past the
board's outer face — doesn't touch any of the 5 `must_survive` checks but
is a translation gap worth tracking.

**3. Eclipse (9/100, not counted).** Ambition 9/15 — the flattest concept
of the three (flagged pre-build: one relief motif carrying the entire
design, socket rank 5's clearance condition flagged as borderline
unfalsifiable) and correspondingly the weakest pick even before the
failure. `session.json` shows the concept-selection round completed
normally (set B chosen, "soft and organic... no hard lip" matching the
dome/dish art direction) but the worker then ran for ~35 minutes into
round-2 style generation before dying with `worker_error`: "Claude's
response exceeded the 32000 output token maximum." Zero recoverable
artifacts — no plan, no manifest, no partial geometry. This is a pipeline
capacity/configuration limitation (`CLAUDE_CODE_MAX_OUTPUT_TOKENS`), not a
signal about the `cad_prompt` (which, per `CAD_PROMPTS.json`'s coverage
block, also fully specified all 5 `must_survive` ranks).
