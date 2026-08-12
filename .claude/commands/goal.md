---
description: Run the board-game vision-fidelity loop (vision → translate → build → repair → score → audit → learn) until the built objects reliably match the vision they were designed from, or a turn cap is reached.
argument-hint: "[max-turns, default 6]"
---

# /goal — board-game vision-fidelity loop

You are the orchestrator. The endgoal is not a good set of ideas and no
longer a sellability score: it is a pair of agents —
`board-game-ideator` (vision) and `board-game-cad-writer` (translation) —
that reliably produce **built objects matching the vision they were designed
from, first shot, with no human intervention.**

Drive the loop with the Task tool. Do not do the subagents' jobs yourself.
The exceptions, which are explicitly yours: pain-point triage (step 14),
merging the question corpus (step 12), and the mechanical audit (step 11).

Parse `$ARGUMENTS` as an optional max-turn cap; default **6**.

## What changed, and why (read before running)

The previous rubric (Differentiation/50 + Producibility/50, 10 ideas, 3
built) stalled for three turns on a problem it could not see: **5 of 9
builds parked on clarifying questions and scored zero, and the builds that
finished lost the design** — parts fused, components absent. The loop was
spending its effort on prior-art search discipline while the actual failure
was the vision→CAD gap.

So: differentiation is now a one-search pass/fail gate. Every turn builds
**3 ideas — one `new`, one `twist`, one `reskin`** — with the production
concept phase, question-answering, and one repair round each. Scoring is
**Vision Fidelity /60 + Build Reliability /25 + Vision Ambition /15**.

**There is no colour anywhere in this pipeline.** The CAD stack has no
colour-assignment step, so every build returns in one uniform material. The
ideator designs in form only, the vision renders are pinned to an unpainted
single-material look so the comparison stays honest, and nothing is scored
on colour. Do not reintroduce it.

## Setup

1. Confirm `board-game/BOARD.md` exists. If missing, stop and tell the user
   the project setup is wrong rather than recreating it.
2. Next turn number `N` = (count of `board-game/history/turn-*` dirs) + 1.
3. **Verify the CAD infra is reachable — required, not optional.** Curl the
   client API (default `http://localhost:4320`); any HTTP response counts as
   reachable, a connection failure does not. If unreachable, **stop before
   spending an ideation pass**: the local-worker Docker stack
   (`docker-compose.local-worker.yml`) and `panda-social-cc-agent`'s
   `tools/client` API server must already be running. This loop never starts
   them.
4. Snapshot agent-file hashes to `board-game/history/turn-<N>/AGENT_HASHES.json`
   — a JSON object mapping each filename in `.claude/agents/` to its sha256.
   `audit_turn.py` uses it to detect mid-turn tampering.

## Phase A — Vision

1. **Ideate.** Invoke `board-game-ideator` in **generate mode**. Tell it only
   the turn number and the mode. Do not paste, summarize, or reference
   `BOARD.md`, `CAD_GRAMMAR.md`, prior `IDEAS.json`, or any past turn — clean
   context is by design (see the agent's own hard rule); you are the one place
   that constraint can leak. Capture its trailing `PAIN_POINTS:` section and
   append it to `board-game/PAIN_POINTS.md` under a new `### Turn <N>` heading
   as an **Ideator:** subsection, right away.
2. **Vision renders.** `python3 board-game/tools/generate_images.py --turn <N>`.
   These are no longer cosmetic — they are the reference the builds get
   compared against, and the ambition judgment is made from them. If the
   script fails (e.g. no `OPENROUTER_API_KEY`), that is a real degradation:
   note it prominently, since ambition and the visual check both get weaker
   without renders. Continue anyway.
3. **Lock ambition.** Invoke `board-game-evaluator` in **ambition mode** for
   turn `N`. It writes `board-game/AMBITION.json` from the specs and renders,
   before any build exists. Never run this after the builds — the entire point
   is that a build outcome cannot contaminate it.
4. **Translate.** Invoke `board-game-cad-writer` in **write mode** for turn
   `N`. It writes `board-game/CAD_PROMPTS.json`. Append its `PAIN_POINTS:` to
   this turn's heading as a **CAD-writer:** subsection.
5. **Back-translation pre-flight.** Run:
   ```
   python3 board-game/tools/generate_images.py --turn <N> \
       --ideas-file board-game/CAD_PROMPTS.json --field cad_prompt \
       --out-dir board-game/history/turn-<N>/backtranslation \
       --latest-dir board-game/backtranslation
   ```
   This renders each `cad_prompt` alone, with no theme text and no sight of
   the vision render. Compare each against its vision render and the idea's
   `must_survive` list. For any feature clearly absent from the
   back-translation, invoke `board-game-cad-writer` in **patch mode** naming
   that specific gap. One patch round only. Twenty seconds here beats thirty
   minutes of CAD discovering the same thing.

## Phase B — Build (3 pilots in parallel)

6. **Spawn three `board-game-cad-pilot` agents in a single message** (three
   tool uses in one turn, so they actually run concurrently), one per idea.
   Give each only its turn number and idea id; its own instructions cover the
   rest. Each drives concept phase → build → question answering → capture →
   deterministic scoring → one repair round, and returns a JSON build report.
7. **Canary (every 4th turn only: N ≡ 0 mod 4).** In the same message, spawn a
   fourth pilot for the control specimen: idea id `0`, prompt file
   `board-game/tools/canary_prompt.txt`, no concept phase, no repair round.
   It is a fixed prompt that never changes, so any movement in its result is
   pipeline drift rather than agent improvement. Skip on other turns.
8. **If zero of the three ideas reached `done`:** stop the loop before
   evaluating. Do not fabricate or skip scores. Report the pilots' terminal
   statuses and reasons so the user can decide whether to fix infra and
   resume. If 1–2 finished, continue — the average covers however many did.

## Phase C — Score

9. **Evaluate.** Invoke `board-game-evaluator` in **score mode** for turn `N`.
   It merges the deterministic measurements with its own visual judgment,
   writes `SCORES.json` + `SCORES.md`, and updates `BOARD.md`,
   `CAD_GRAMMAR.md` and `PAIN_POINTS.md`. Parse its final
   `AVERAGE_SCORE:` line; if unparseable, read `SCORES.json` rather than
   guessing.
10. **Contact sheet.** `python3 board-game/tools/contact_sheet.py --turn <N>`.
    One image: vision | first shot | QA views | after repair, per idea. This
    is the five-second human check on the turn — mention its path in your
    report.

## Phase D — Integrity

11. **Mechanical audit (yours).** `python3 board-game/tools/audit_turn.py --turn <N>`.
    Exit 0 green, 1 amber, 2 red.
12. **Judged audit.** Invoke `board-game-auditor` for turn `N`. It reads the
    mechanical findings plus raw artifacts and appends its own verdict to
    `board-game/INTEGRITY.md`.
13. **Act on the verdict.**
    - **RED from either audit: stop the loop.** Report the finding verbatim.
      A red means the turn's numbers cannot be trusted or an agent did
      something it was forbidden to do; running another turn on top of it
      compounds the problem. Do not attempt to fix a red yourself beyond
      reverting an unauthorized file change.
    - **AMBER:** continue, and feed every amber finding into triage (step 14).
    - **GREEN:** continue.

## Phase E — Learn

14. **Question corpus (yours).** Read every `answer` event in this turn's
    `board-game/history/turn-<N>/builds/idea-*/session.json` and append them
    to `board-game/CAD_QUESTIONS.md` under `### Turn <N>`: the question
    verbatim, the answer given, the `source_field` cited, and which recurring
    category it belongs to (create the file with a
    `# CAD QUESTIONS — what the pipeline asks when a prompt leaves a gap`
    header if absent). Group by category, not by idea — the categories are
    what the cad-writer's template has to pre-answer, and the metric that
    matters is questions-asked trending to zero.
15. **Pain-point triage (yours).** Read everything appended to
    `PAIN_POINTS.md` since the last `**Triage:**` entry, plus every AMBER
    audit finding. For each item:
    - *Uncontroversial* (one obviously-correct fix: ambiguous wording, a
      script bug, a stale field reference, a path papercut) — fix it directly
      via Edit, in `.claude/agents/*.md` (outside any Learned Heuristics
      section, which belongs to that agent's own revise mode),
      `.claude/commands/goal.md`, or `board-game/tools/*`. **Cap: 3 auto-fixes
      per turn**; log the rest as deferred.
    - *Controversial* (scoring weights, the rubric shape, the ambition floor,
      the 3-idea mix, the repair-round cap, cost/architecture, or anything
      with a real tradeoff) — use `AskUserQuestion` with your recommendation
      and 1–2 alternatives. Apply only what the user approves. Never change a
      weight, threshold, or the pipeline's shape without explicit approval,
      however strongly a pain point argues for it.
    - *Not actionable* — acknowledge and move on.
    - Every item gets one line under a `**Triage:**` subsection of this turn's
      heading: `- [AUTO-FIXED|DEFERRED|ASKED-APPROVED|ASKED-DECLINED|NOT-ACTIONABLE] <item> — <what and why>`.
    - Never edit `IDEAS.json`, `SCORES.*`, `BOARD.md`, `CAD_GRAMMAR.md` or
      `INTEGRITY.md` content here — those are outputs, not inputs. Edits to
      this file take effect on the *next* invocation, not mid-run.
16. **Archive.** Copy `IDEAS.json`, `CAD_PROMPTS.json`, `SCORES.json`,
    `SCORES.md` and `AMBITION.json` into `board-game/history/turn-<N>/`.
    Builds, images and the contact sheet are already written there. Never
    archive `board-game/tools/`, `BOARD.md`, `CAD_GRAMMAR.md`,
    `CAD_QUESTIONS.md`, `PAIN_POINTS.md` or `INTEGRITY.md` — those are
    running cross-turn records.
17. **Report** in one or two lines, e.g.:
    `Turn 14: avg 72.3/100, first-shot survival 73% (3/3 built, 4 questions). Audit AMBER (1 provenance finding). Contact sheet: .../contact-sheet-turn-14.png. Continuing…`

## Phase F — Stop or revise

18. **Stopping condition.** Stop and report success when **two consecutive
    turns** have every built idea at **≥80% rank-weighted `must_survive`
    survival on the first shot**, with every idea clearing the 8/15 ambition
    floor. This is deliberately not an average: an average lets one clean
    reskin carry two failures, and the thing being proven is reliability.
    On success, point the user at the Learned Heuristics sections of
    `board-game-ideator.md` and `board-game-cad-writer.md`, and at
    `CAD_GRAMMAR.md` — those three are the durable artifacts this pipeline
    exists to produce.
19. **Cap reached** (`N >= max-turns`): stop, show the Score History trend
    from `BOARD.md`, and suggest raising the cap or reviewing
    `BOARD.md`/`CAD_GRAMMAR.md`/`INTEGRITY.md` by hand. Do not silently
    continue past the cap.
20. **Otherwise, revise — two separate passes, in this order:**
    - `board-game-cad-writer` in **revise mode** (folds `CAD_QUESTIONS.md`
      and `CAD_GRAMMAR.md` into its prompt template).
    - `board-game-ideator` in **revise mode** (folds `BOARD.md` and
      `CAD_GRAMMAR.md` into its vision heuristics).
    Append each one's `PAIN_POINTS:` under this turn's heading as
    **CAD-writer (revise):** / **Ideator (revise):** — they get triaged next
    turn. Then increment `N` and go to Phase A.

## Notes

- Every subagent invocation is a fresh Task call. Cross-turn memory flows
  only through the files — that is the point: improvement has to survive as
  an artifact, not as your context.
- Wall clock is roughly 1.5–2 h per turn (concept ~5 min, build ~30 min,
  repair ~30 min, three ideas in parallel). If that is too slow, the repair
  round is the first thing to cut — it is diagnostic, never scored.
- The three pilots must be spawned in **one message with three tool uses**,
  or they run sequentially and the turn takes three times as long.
- Attribution is the loop's most valuable output. Every fidelity loss is
  either a translation failure (cad-writer), a vision failure (ideator), or a
  pipeline limitation (neither — design around it). The evaluator is required
  to attribute each one; if `BOARD.md` entries stop doing that, raise it.
- If triage finds itself making the same kind of edit turn after turn,
  surface that to the user as an observation rather than quietly repeating it.
- Retired on 2026-08-11: `generate_cad_builds.py` (fire-and-wait, could not
  answer parks) is superseded by `cad_session.py` + `board-game-cad-pilot`,
  and the 20-persona purchase-intent panel stays paused — three straight
  turns of unanimous 0/20 driven by prototype-render appearance rather than
  desirability. Re-enabling either requires an explicit instruction here, not
  an automatic revival.
