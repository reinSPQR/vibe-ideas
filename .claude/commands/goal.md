---
description: Run the board-game-ideator self-improvement loop (ideate → evaluate → revise) until the average sellability score hits 80+, or a turn cap is reached.
argument-hint: "[max-turns, default 6]"
---

# /goal — board-game-ideator self-improvement loop

You are the orchestrator for the loop described in `idea.md`. The endgoal is
not a good set of ideas — it's a `board-game-ideator` agent
(`.claude/agents/board-game-ideator.md`) that reliably produces idea sets
averaging **80+/100** on the sellability rubric. Drive the loop below using
the Task tool to invoke the `board-game-ideator` and `board-game-evaluator`
subagents. Do not do their jobs yourself — delegate and orchestrate.

Parse `$ARGUMENTS` as an optional max-turn cap; default to **6** if not
given or not a number.

## Setup

1. Ensure `board-game/BOARD.md` exists (it should already — if missing,
   stop and tell the user something is wrong with the project setup rather
   than recreating it yourself).
2. Determine the next turn number `N`: look at `board-game/history/` and
   use `(number of existing `turn-*` subdirectories) + 1`. Start at 1 if the
   directory is empty or doesn't exist.

## Loop (repeat until stopping condition below)

For the current turn `N`:

1. **Ideate.** Invoke the `board-game-ideator` subagent in **generate
   mode**: tell it only that this is turn `N`, generate mode, and to follow
   its own instructions. Do **not** paste, summarize, or reference
   `board-game/BOARD.md`, past `IDEAS.md`/`SCORES.md`, or any prior turn's
   content in the prompt you give it — generate mode must run with a clean
   context, by design (see the agent's own "Hard rule" under Generate
   mode). You are the one place that constraint could leak through
   accidentally, so keep this prompt minimal.
2. **Snapshot the ideator file.** Before evaluating, note the current
   content/hash of `.claude/agents/board-game-ideator.md` so you can detect
   if it changes when it shouldn't.
3. **Evaluate.** Invoke the `board-game-evaluator` subagent: tell it this is
   turn `N`, and to score `board-game/IDEAS.md`, write
   `board-game/SCORES.md`, and update `board-game/BOARD.md` per its
   instructions.
4. **Verify the ideator was untouched.** Compare
   `.claude/agents/board-game-ideator.md` against the snapshot from step 2.
   If it changed, the evaluator violated its hard rule — stop the loop,
   revert the unauthorized change (the evaluator's only legitimate writes
   are `SCORES.md`/`BOARD.md`), and report this to the user as a pipeline
   bug rather than continuing as if nothing happened.
5. **Parse the score.** Extract the `AVERAGE_SCORE: <XX.X>` line from the
   evaluator's reply. If it's missing or unparseable, read
   `board-game/SCORES.md` directly to recover the average instead of
   guessing.
6. **Archive the turn.** Copy the turn's `board-game/IDEAS.md` and
   `board-game/SCORES.md` into `board-game/history/turn-<N>/` (create the
   directory). Keep the top-level `IDEAS.md`/`SCORES.md` as the
   "latest turn" copies — don't delete them, just also archive them. Do
   **not** archive `board-game/tools/` — those are the ideator's persistent
   toolkit, not per-turn artifacts.
7. **Report progress** to the user in one short line, e.g.:
   `Turn 3: avg 71.2/100 (target 80). Continuing…`
8. **Check the stopping condition:**
   - If average score **>= 80**: stop the loop. Report success — final
     score, turn number, and point the user at
     `.claude/agents/board-game-ideator.md` (the "Learned Heuristics"
     section) as the durable artifact this pipeline was built to produce.
     Do not run a revise step for this turn — there is nothing left to
     improve for.
   - If `N >= max-turns`: stop the loop. Report that the cap was hit
     without reaching 80, show the score trend from `board-game/BOARD.md`'s
     Score History table, and suggest either raising the cap
     (`/goal <higher-number>`) or reviewing `BOARD.md` lessons manually —
     don't just silently keep going past the cap.
   - Otherwise: **Revise.** Invoke `board-game-ideator` in **revise mode**:
     tell it to read `board-game/BOARD.md` and update its own "Learned
     Heuristics" section in `.claude/agents/board-game-ideator.md`
     accordingly. Then increment `N` and go back to step 1.

## Notes

- Each subagent invocation should be a fresh Task call — don't try to reuse
  conversation state between turns; all cross-turn memory must flow through
  `board-game/BOARD.md` and the ideator's own file, by design (that's the
  point of the pipeline: the improvement has to survive as an artifact, not
  as your context).
- If a Task invocation fails or a subagent doesn't produce the expected
  file, stop and surface the failure rather than fabricating scores or
  silently retrying in a loop.
- Keep your own narration terse — one line of progress per turn plus a
  final summary. The interesting output is the files, not your commentary.
