---
description: Run the board-game-ideator self-improvement loop (ideate → CAD build → evaluate → revise) until the average sellability score hits 80+, or a turn cap is reached.
argument-hint: "[max-turns, default 6]"
---

# /goal — board-game-ideator self-improvement loop

You are the orchestrator for the loop described in `idea.md`. The endgoal is
not a good set of ideas — it's a `board-game-ideator` agent
(`.claude/agents/board-game-ideator.md`) that reliably produces idea sets
whose *built, photographed, panel-tested* picks average **80+/100** on the
sellability rubric (Differentiation /50, Producibility /40, Buyability
/10). Drive the loop below using the Task tool to invoke the
`board-game-ideator` and `board-game-evaluator` subagents. Do not do their
jobs yourself — delegate and orchestrate. The one exception is the new
pain-point triage step below, which is explicitly your own job, not a
subagent's.

Parse `$ARGUMENTS` as an optional max-turn cap; default to **6** if not
given or not a number.

## Setup

1. Ensure `board-game/BOARD.md` exists (it should already — if missing,
   stop and tell the user something is wrong with the project setup rather
   than recreating it yourself).
2. Determine the next turn number `N`: look at `board-game/history/` and
   use `(number of existing `turn-*` subdirectories) + 1`. Start at 1 if the
   directory is empty or doesn't exist.
3. **Verify the local CAD build infra is reachable — required, not
   optional.** Under the current rubric, Producibility and Buyability are
   scored entirely from a real CAD build and a real purchase-intent panel,
   so this loop cannot produce a valid score without that infra running.
   Issue a lightweight GET against the client API base URL (default
   `http://localhost:4320`) via Bash/curl — the same reachability
   convention `generate_cad_builds.py` uses internally (any HTTP response,
   even an error status, counts as reachable; a connection failure does
   not). If unreachable: **stop here, before spending an ideation pass.**
   Tell the user plainly that the local-worker Docker stack
   (`docker-compose.local-worker.yml`) and `panda-social-cc-agent`'s
   `tools/client` API server need to be running, and that this loop never
   starts them itself. Do not proceed to the Loop below until infra is
   confirmed up.

## Loop (repeat until stopping condition below)

For the current turn `N`:

1. **Ideate.** Invoke the `board-game-ideator` subagent in **generate
   mode**: tell it only that this is turn `N`, generate mode, and to follow
   its own instructions. Do **not** paste, summarize, or reference
   `board-game/BOARD.md`, past `IDEAS.json`/`SCORES.md`, or any prior turn's
   content in the prompt you give it — generate mode must run with a clean
   context, by design (see the agent's own "Hard rule" under Generate
   mode). You are the one place that constraint could leak through
   accidentally, so keep this prompt minimal. Its reply ends with a
   `PAIN_POINTS:` section (outside the `IDEAS.json` it wrote) — capture it
   and append it to `board-game/PAIN_POINTS.md` right away, under a new
   `### Turn <N>` heading, as an **Ideator:** subsection (create the file
   with a "# PAIN POINTS — Pipeline Execution Log" header if it doesn't
   exist yet). Doing this now, before step 6, means the evaluator's own
   pain-points write-up lands under the same heading instead of creating a
   duplicate.
2. **Visualize (best-effort, non-blocking).** Run
   `python3 board-game/tools/generate_images.py --turn <N>` via Bash. This
   renders each idea's `prompt` field to a PNG with `openai/gpt-image-2`
   (via OpenRouter) purely so the user can eyeball the set — it is not part
   of scoring and must never gate or fail the turn. Read the script's
   summary line (`IMAGES: x/10 generated`) and mention it in your progress
   report; if it exits non-zero (e.g. `OPENROUTER_API_KEY` isn't set), note
   that previews were skipped and continue the loop exactly as if this step
   didn't exist. Images land in `board-game/history/turn-<N>/images/`, with
   a "latest turn" convenience copy mirrored into `board-game/images/`.
3. **Run CAD builds — required, not best-effort.** Run
   `python3 board-game/tools/generate_cad_builds.py --turn <N>` via Bash.
   This submits the ideator's `cad_build_picks` (3 ideas) as real `create`
   jobs through `panda-social-cc-agent`'s local-worker Docker stack, polls
   them to completion, and downloads each build's plain CAD render, QA
   sheet, and a photoreal product photo (via the real production
   `ai_thumbnail` code, shelled out to inside the worker container) into
   `board-game/history/turn-<N>/cad-builds/`. Read its
   `CAD_BUILDS: x/3 done, y parked, z failed` summary line and mention it
   in your progress report.
   - Under the current rubric this step's output is not optional context —
     it *is* what gets scored. If it exits non-zero because **zero**
     builds completed: retry it once (transient infra hiccups happen). If
     it still produces zero successful builds on retry, **stop the loop**
     — do not proceed to evaluate, do not fabricate or skip a score for
     this turn. Report to the user with the exact error/park output so
     they can diagnose (infra down mid-run, a Docker worker crashed,
     etc.), and let them decide whether to fix infra and resume with
     `/goal` or investigate further. This is a real behavior change from
     the old best-effort treatment of this step — the CAD reality check
     used to be a bonus signal you could silently skip; now it's the
     scoring mechanism itself.
   - If 1-3 builds completed, proceed normally — the turn's average is
     computed over however many builds actually succeeded (see step 8).
4. **Purchase-intent panel (only if step 3 produced at least one
   successful build).** Read `board-game/tools/customer_personas.json`
   (20 fixed persona descriptions). For each persona, spawn one `Agent`
   call — all 20 in a single message so they run in parallel — with a
   prompt built from: that persona's description, the built ideas' photo
   paths (each build's `manifest.json` has a `photo_file` field — the
   extension varies, e.g. `.jpg` or `.png`, since the real thumbnail
   pipeline corrects it to match whatever format the model actually
   returns) plus their `concept`/`rules` text (from `board-game/IDEAS.json`),
   and an
   instruction to give one YES/NO buy verdict + one-line reason per
   product in a strict, parseable format, explicitly assuming
   price/budget is not a constraint. Collect all 20 replies, tally YES
   votes per product (drop any persona call that errored from the
   denominator rather than blocking), and write
   `board-game/history/turn-<N>/cad-builds/purchase-intent.json`: for each
   built idea, its `id`, `title`, `would_buy` count, panel size actually
   tallied, and the list of one-line reasons. If step 3 produced zero
   successful builds, this step never runs (the loop already stopped in
   step 3).
5. **Snapshot the ideator file.** Before evaluating, note the current
   content/hash of `.claude/agents/board-game-ideator.md` so you can detect
   if it changes when it shouldn't.
6. **Evaluate.** Invoke the `board-game-evaluator` subagent: tell it this is
   turn `N`, and to score `board-game/IDEAS.json`, write
   `board-game/SCORES.md`, and update `board-game/BOARD.md` per its
   instructions — Producibility and Buyability for the built ideas now come
   directly from `cad-builds/` and `purchase-intent.json`. It also appends
   its own **Evaluator:** subsection to `board-game/PAIN_POINTS.md` under
   this turn's `### Turn <N>` heading (already created in step 1).
7. **Verify the ideator was untouched.** Compare
   `.claude/agents/board-game-ideator.md` against the snapshot from step 5.
   If it changed, the evaluator violated its hard rule — stop the loop,
   revert the unauthorized change (the evaluator's only legitimate writes
   are `SCORES.md`/`BOARD.md`/`PAIN_POINTS.md`), and report this to the
   user as a pipeline bug rather than continuing as if nothing happened.
8. **Parse the score.** Extract the `AVERAGE_SCORE: <XX.X or N/A>` line
   from the evaluator's reply. If it's missing or unparseable, read
   `board-game/SCORES.md` directly to recover the average instead of
   guessing. This average is now computed **only over the built ideas**
   (1-3 of them, per step 3) — the other, unbuilt ideas contribute a
   Differentiation score for lessons-learned purposes only and are not
   part of the average. `N/A` should not occur in practice (step 3 already
   stops the loop before evaluate if zero builds succeeded) — if you see
   it anyway, treat it the same way: stop and surface it rather than
   guessing a number.
9. **Pain-point triage.** This step is yours to execute directly, not a
   subagent's. Read everything appended to `board-game/PAIN_POINTS.md`
   since the last `**Triage:**` entry (i.e. this turn's Ideator +
   Evaluator subsections, plus any leftover un-triaged entries from
   before). For each individual pain point listed:
   - **Classify it:**
     - *Uncontroversial*: a clear, low-risk fix with one obviously-correct
       resolution — ambiguous wording, a missing example, a script bug, a
       stale reference to a removed field, a tooling/file-path papercut.
     - *Controversial*: touches scoring weights or the rubric shape, the
       80/100 stopping target, the 3-build cap, cost/scope/architecture,
       or has multiple reasonable fixes with a real tradeoff between them.
     - *Not actionable*: an inherent constraint with no fix (e.g. "builds
       take ~20 minutes") — acknowledge and move on.
   - **Uncontroversial items**: fix them directly via Edit, in whichever
     file is implicated — `.claude/agents/board-game-ideator.md` (outside
     its Learned Heuristics section, which is the ideator's own to edit in
     revise mode — you may still fix other sections here, since that's
     exactly the "explicit triage instruction" carve-out the ideator's
     revise-mode rule allows), `.claude/agents/board-game-evaluator.md`,
     this file (`.claude/commands/goal.md`), `board-game/tools/*.py`, or
     `board-game/tools/customer_personas.json`. **Cap yourself at 3
     auto-fixes per turn** to bound blast radius; if there are more
     uncontroversial candidates than that, apply the 3 most impactful and
     log the rest as deferred for a future turn's triage pass.
   - **Controversial items**: use `AskUserQuestion` — present the pain
     point, your recommended fix if you have one, and 1-2 alternatives.
     Only apply a change if the user approves it.
   - **Every item**, regardless of disposition, gets one line appended
     under a new `**Triage:**` subsection of this turn's `### Turn <N>`
     heading in `board-game/PAIN_POINTS.md`:
     `- [AUTO-FIXED|DEFERRED|ASKED-APPROVED|ASKED-DECLINED|NOT-ACTIONABLE] <pain point> — <what was done and why>`.
   - **Guardrails**: never touch `board-game/IDEAS.json`, `SCORES.md`, or
     `BOARD.md` content in this step — those are the agents' own scoring
     outputs. Never change a scoring weight, threshold, or the pipeline's
     shape (Differentiation/50, Producibility/40, Buyability/10, the
     80/100 target, the 3-build cap, panel size) without explicit user
     approval, even if a pain point seems to argue for it — that's always
     controversial by definition, never an auto-fix. If you edit this file
     (`goal.md`) mid-run, note that it only affects the *next* `/goal`
     invocation — this run's instructions are already loaded and won't
     change retroactively mid-loop.
10. **Archive the turn.** Copy the turn's `board-game/IDEAS.json` and
    `board-game/SCORES.md` into `board-game/history/turn-<N>/` (create the
    directory) — images from step 2 and `cad-builds/` (including
    `purchase-intent.json`) from steps 3-4 are already written directly
    there and need no separate top-level "latest" mirror, unlike
    `IDEAS.json`/`SCORES.md`. Do **not** archive `board-game/tools/` (the
    ideator's persistent toolkit) or `board-game/PAIN_POINTS.md` (a running
    cross-turn log, like `BOARD.md` — never per-turn-copied).
11. **Report progress** to the user in one short line, e.g.:
    `Turn 3: avg 71.2/100 (3/3 built, target 80), 10/10 previews rendered, panel avg 7.4/10 buyability. Pain-points: 2 auto-fixed, 1 asked (declined). Continuing…`
    (Adjust the built-count and pain-points clauses to what actually
    happened — omit "Pain-points: ..." entirely if there were none this
    turn.)
12. **Check the stopping condition:**
   - If average score **>= 80**: stop the loop. Report success — final
     score, turn number, and point the user at
     `.claude/agents/board-game-ideator.md` (the "Learned Heuristics"
     section) as the durable artifact this pipeline was built to produce.
     Do not run a revise step for this turn — there is nothing left to
     improve for.
   - If `N >= max-turns`: stop the loop. Report that the cap was hit
     without reaching 80, show the score trend from `board-game/BOARD.md`'s
     Score History table, and suggest either raising the cap
     (`/goal <higher-number>`) or reviewing `BOARD.md`/`PAIN_POINTS.md`
     manually — don't just silently keep going past the cap.
   - Otherwise: **Revise.** Invoke `board-game-ideator` in **revise mode**:
     tell it to read `board-game/BOARD.md` and update its own "Learned
     Heuristics" section in `.claude/agents/board-game-ideator.md`
     accordingly. Its reply ends with its own `PAIN_POINTS:` section too —
     append it to `board-game/PAIN_POINTS.md` under this same turn's
     `### Turn <N>` heading, as an **Ideator (revise pass):** subsection
     (it'll get triaged at the start of the *next* turn's step 9, along
     with whatever fresh pain points that turn produces). Then increment
     `N` and go back to step 1.

## Notes

- Each subagent invocation should be a fresh Task call — don't try to reuse
  conversation state between turns; all cross-turn memory must flow through
  `board-game/BOARD.md`, `board-game/PAIN_POINTS.md`, and the ideator's own
  file, by design (that's the point of the pipeline: the improvement has to
  survive as an artifact, not as your context).
- If a Task invocation fails or a subagent doesn't produce the expected
  file, stop and surface the failure rather than fabricating scores or
  silently retrying in a loop.
- Keep your own narration terse — one line of progress per turn plus a
  final summary. The interesting output is the files, not your commentary.
- Image previews (step 2) need `OPENROUTER_API_KEY` in the environment (or
  a `.env` at the repo root). If it's missing, `generate_images.py` prints
  a clear message and exits non-zero — treat that as informational, not an
  error to fix or escalate; it's cosmetic and doesn't affect scoring.
- CAD builds (step 3) need `panda-social-cc-agent`'s local-worker Docker
  stack (`docker-compose.local-worker.yml`) and its `tools/client` API
  server already running — this loop never starts either itself, and Setup
  step 3 already checks for this before the turn begins. If infra goes
  down *mid-turn* (after Setup's check passed), step 3's own retry-then-
  stop handling covers it.
- The purchase-intent panel (step 4) is 20 parallel `Agent` calls — send
  them as one message with 20 tool uses so they actually run concurrently,
  not 20 sequential Task calls.
- The pain-point triage step (step 9) is bounded by design: at most 3
  auto-fixes per turn, and anything touching scoring/architecture always
  goes through `AskUserQuestion` rather than being auto-applied. If triage
  starts feeling like it's making the same kind of edit turn after turn,
  that's itself worth surfacing to the user as an observation, not just
  quietly repeating the fix.
