# Sellability Scores — Turn 15

Rubric: Vision Fidelity/60 + Build Reliability/25 + Vision Ambition/15 = /100.
Only the first-shot build is scored for Fidelity; Reliability is 0 whenever
the first shot didn't reach `done`. See `board-game/AMBITION.json` for the
locked pre-build Ambition scores.

## Summary

| # | Title | Path | Ambition /15 | Fidelity /60 | Reliability /25 | Total /100 | Build status | Counted? |
|---|-------|------|---------------:|----------------:|--------------------:|-------------:|---------------|----------|
| 1 | Lockstep Canals | new | 12 | 0 | 0 | 12 | **failed** (terminal failure ~35min after concept selection, mid-CAD-generation) | no |
| 2 | Sluice Row | twist | 9 | 32.0 | 21.23 | 62.23 | done | **yes** |
| 3 | Tidepool Stones | reskin | 9 | 0 | 0 | 9 | **failed** (2 attempts; 1st failed pre-park, 2nd failed ~47min after concept selection) | no |

**Average (counted ideas): 62.23 / 100** (idea 2 only)
**First-shot must_survive survival: 53%** (idea 2 only; 18% across all 3 ideas including the two that never reached a build)

All three ideas pass the novelty gate (one confirming search each, none
contradicted). Ideas 1 and 3 are excluded from the average not for novelty
or low ambition — both clear the 8/15 floor — but because neither ever
produced a first-shot build artifact. Both progressed *past* concept
selection into full CAD generation this time (unlike Turn 14's two
pre-build failures, which died at plan-generation/concept-phase before a
job even started) and then died with a bare `terminal: failed` event 35-47
minutes later, with no error string, plan, manifest, or partial geometry
recorded in `session.json`. There is nothing to measure Fidelity or
Reliability against, so both total their Ambition score alone and that
total is not comparable to idea 2's real build outcome.

## Per-idea notes

**1. Lockstep Canals (12/100, not counted).** Ambition 12/15 — the most
three-dimensional concept of the batch on paper: four distinct stone-shape
families (straight/corner/tee/cross) each carrying a carved trench, tally
notches, and 45-degree chamfers, plus a genuinely different font-stone part
(basin + owner holes) and an open corner draw bin. None of that was ever
built: `session.json` shows `submit` → `parked` (`awaiting_concept_selection`,
2m34s) → `select_concept` (set B, "weathered stone-canal heritage," chosen
for tool-marked relief over the machined/toy-plastic alternatives) → the job
then ran for ~35 more minutes before reaching **`terminal: failed`** with no
further detail. No capture, no `evaluation_report.json`, no `project/` or
`renders/` directory. The `cad_prompt` in `CAD_PROMPTS.json` is fully
specified (42-component separation requirement, all 4 stone families, all 5
`must_survive` ranks covered) — nothing in the prompt content predicts this
outcome; this is a pipeline failure during CAD generation itself, a later
failure point than Turn 14's pre-job failures but still upstream of any
geometry the ideator or CAD-writer controls.

**2. Sluice Row (62.23/100, counted).** The only build to reach `done` this
turn. Of the 5 `must_survive` ranks, only rank 1 (49/49 components discrete,
weight 5) got a clean geometric `pass`. Ranks 2 (capacity ring count),
3 (seed_small count), and 4 (store_pit count) all came back geometric `fail`
with `detail: "no geometry could be bound to the named part(s)"`, and rank 5
(large-seed radial clearance) came back geometric `fail` on a measured
0.0mm minimum distance. Reading `project/main.py` splits these into two very
different stories. Ranks 2 and 4 are a **real, attempted-but-lost feature**:
the capacity rings and both store wells are genuinely modeled — cut as
boolean subtractions into the single `trough_board` solid — but never
surfaced as separately-named parts, so the checker (which needs a bindable
named part per rank) correctly reports them absent even though the geometry
exists. This reads as a **pipeline/translation limitation**: a subtractive
feature on a monolithic board is architecturally invisible to a
part-name-prefix checker no matter how faithfully it's cut. Confirmed
visually too — an ortho top-down close-up on any of the 12 small wells
(`project/main_review/trough_board.png`) shows a plain circular recess with
no ring line on the interior wall at all (the 1mm x 0.5mm ring sits
mid-depth on a vertical wall, invisible from directly above), so rank 2
scores 0 on both checks. Rank 4 scores better visually: the top-down whole-
board view clearly shows the two 55mm store wells dwarfing the twelve 26mm
small wells, a clean visual pass, so rank 4's blended credit is 0.5. Rank 3
is a different case: `content.json` and the STEP manifest both list
`seed_small_01` through `seed_small_16` as 16 correctly-named, separate
top-level parts, and every render examined (staged rows beside the board,
grouped by size) shows three unmistakably different cylinder diameters side
by side — this looks like a **scorer defect**, not an absent feature, but
per rubric the geometric axis is consumed as reported (fail, 0 credit) while
the visual axis still earns its own credit (pass, 1.0), giving rank 3 a
blended 0.5. Rank 5's press-fit finding (0.0mm clearance) also does not match
the renders: `validate()` in `main.py` asserts a 4mm radial gap and every
top-down close-up on a filled well (`qa.png`) shows a clean, unbroken gap
ring around every seated seed-weight, including the larger ones — visual
credit 1.0 against geometric 0, blended 0.5. Weighted total:
(5×1.0 + 4×0 + 3×0.5 + 2×0.5 + 1×0.5) / 15 × 60 = **32.0/60**
(geometric_fidelity 0.3333 exactly matches `evaluation_report.json`;
visual_fidelity 0.7333 is the evaluator's own read). No `must_survive` rank
certifies a stacked-layer or enclosed-cavity dimension, and a playability
pass (26mm-dia/16mm-deep small wells, 7mm-tall seeds sitting flush with the
floor and 9mm below the rim, single flat layer, no occlusion) found no reach
or sight failure, so no additional Fidelity penalty applies. Reliability: 15
base − 2 (one concept-selection question) + 8.23 (independent
`printability_0_10`) = **21.23/25**. The pipeline's own `review_fix.printability`
scored a perfect 10 in "printability-only" mode against the independent
scorer's 8.23 (flagging "49 disconnected mesh components" on the assembly) —
49/49 is the correct, intended count (board + 48 loose seeds, matching the
rank-1 pass), so this is the same non-fusion print-planning-risk pattern
`CAD_GRAMMAR.md` already documented for Turn 14, not a red flag.

**3. Tidepool Stones (9/100, not counted).** Ambition 9/15 — the flattest
concept of the three (flagged pre-build: declared as an exact reskin with
zero rule change, one repeated part type stamped 64 times, most of the
identity carried by a single dual-relief disc). `session.json` shows two
full attempts: the first job (submitted 04:54:54) reached `terminal: failed`
in ~80 seconds, before ever parking — no plan, no question, nothing. The
orchestrator resubmitted the identical prompt at 04:56:28; that job parked
normally, a concept was selected (set B, "organic and tidepool-soft," chosen
for the sea-smoothed ridge/hollow language over the crisp-minimal and
chunky-industrial alternatives), and then the job ran for ~47 more minutes
before reaching **`terminal: failed`** again, with no further detail in
either case. No capture, no `evaluation_report.json`, no project or render
artifacts from either attempt. The `cad_prompt` is fully specified (65-
component separation, both disc-face relief counts, board-socket count, all
5 `must_survive` ranks covered) — as with idea 1, nothing in the prompt
content predicts this outcome; it is a pipeline failure during CAD
generation, occurring twice on the same idea.
