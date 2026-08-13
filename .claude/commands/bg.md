---
description: Advance the board-game pipeline by exactly one step — the queue decides which idea and which stage. Designed to be driven by /loop.
argument-hint: "[slug — optional, to force one idea]"
---

# /bg — one step of the board-game pipeline

The goal is a **good CAD model**: one that prints, one that plays, one the
owner approves. Improving the agents is only how we get there.

**Do exactly one action, then stop.** Not two, not "while I'm here". This
command is meant to be run under `/loop /bg`, and a step that quietly does
three things is a step nobody can inspect. If the action finishes early, still
stop — the next invocation picks up the next one.

## Poll first

```bash
.venv/bin/python board-game/tools/telegram.py poll
```

One pass, always, before deciding anything — the owner may have tapped a
button or answered a reply-reason since the last step, and that can change
what `next` should return (an `approve` moves an idea out of
`awaiting_owner`, for instance). `poll` only ever executes what a gate
message itself offered (`approve`/`reject`/`rework`/`ship`/`amend`), gated
by `pipeline_queue.py`'s own state check, so this is safe to run every time
even when nothing is waiting. If Telegram isn't configured it prints
"nothing to poll" and this is a no-op.

## Decide

```bash
.venv/bin/python board-game/tools/pipeline_queue.py next
```

That prints one JSON object naming the `slug` and the `action`. **You do not
choose** — the queue owns prioritisation (ideas closest to shipping go first,
so finishing beats starting) and it owns the repair budget. If `$ARGUMENTS`
names a slug, still run `next` and simply skip to that idea's own action.

Then run the matching block below, and nothing else.

## Actions

### `propose`
Invoke `board-game-ideator` in **propose** mode. It writes
`board-game/ideas/<slug>/idea.json` and runs `rules_check.py` itself. Then:

```bash
.venv/bin/python board-game/tools/pipeline_queue.py add <slug> --title "<title>"
```

Append its `PAIN_POINTS:` to `board-game/PAIN_POINTS.md` under a dated heading.

### `rules_gate`
First check whether this idea is at `proposed` because the owner sent it back
for rework (`QUEUE.json`'s entry has a non-empty `rework_reason`) rather than
because it is new or just failed the gate. If so, invoke `board-game-ideator`
in **rework** mode with the owner's `rework_reason` verbatim *before* running
the gate — an owner rework must actually change the idea, not just re-pass an
unmodified `idea.json` and walk it straight back to the same render the owner
already sent back. No separate bookkeeping needed afterward: the next
successful `rules_gate` run below moves the idea out of `proposed` anyway,
and a later owner rework overwrites `rework_reason` with its own new reason.

Then:
```bash
.venv/bin/python board-game/tools/rules_check.py board-game/ideas/<slug>/idea.json
```
PASS → `pipeline_queue.py advance <slug> --to rules_ok`.
FAIL → invoke `board-game-ideator` in **rework** mode with the findings
verbatim; leave the state at `proposed` so the gate runs again next step.

### `brief`
Invoke `board-game-brief-writer` in **write** mode. It writes `brief.json` +
`brief.md` and runs `ergonomics_check.py` itself. Verify it actually passed:

```bash
.venv/bin/python board-game/tools/ergonomics_check.py board-game/ideas/<slug>/brief.json
```

PASS → `advance --to briefed`. FAIL → **patch** mode with the findings; stay
put. Append its `PAIN_POINTS:`.

### `draft`
Invoke `board-game-builder` in **draft** mode. It builds real geometry fast
and renders it — this is not an illustration, it is the object, and the render
it produces becomes the visual contract if the owner says yes.

`advance --to drafted`.

### `owner_gate_1`
```bash
.venv/bin/python board-game/tools/telegram.py gate1 <slug>
```
Sends the hero render, a one-screen rules summary and the bill, with the three
reply commands. Then `advance --to awaiting_owner` and **stop**. Do not guess
what the owner would say; the whole point of this gate is that a human decides
which games are worth making.

### `build`
Invoke `board-game-builder` in **build** mode. It must read every image in
`board-game/ideas/<slug>/reference/` first — the owner approved that
silhouette. Then:

```bash
.venv/bin/python board-game/tools/gate.py board-game/ideas/<slug>/project \
    --bill board-game/ideas/<slug>/project/bill.json
```

`GATE PASS` → `advance --to built`.
`GATE FAIL` → `pipeline_queue.py repair <slug>`:
- exit 0 → invoke `board-game-builder` in **repair** mode with the gate's
  findings verbatim, then re-run `gate.py`.
- exit 1 (budget exhausted) → **arbitration**: read `brief.json`, `gate.json`
  and the build source, and decide whether what remains is a genuine spec
  conflict — the brief demanding things that are mutually impossible — rather
  than a build defect. If it is, write `brief_proposed.json` alongside the
  brief with the minimum set of numbers changed and an `amendments` array
  saying what each change trades away; **never** edit `brief.json` yourself.
  Then `telegram.py arbitration <slug>` (or `telegram.py stuck <slug>` if it
  is not a spec conflict) and `advance --to blocked`.

### `panel`
Spawn all three lenses **in a single message with three tool uses** so they
run concurrently and cannot see each other's reasoning:
`board-game-lens-printability`, `board-game-lens-fidelity`,
`board-game-lens-playability`.

All three PASS → `advance --to reviewed`.
Any FAIL → treat exactly like a gate failure: `pipeline_queue.py repair <slug>`, then
builder **repair** mode with the failing verdicts, then re-run only the lenses
that failed. Budget exhausted → arbitration, as above.

### `owner_gate_2`
```bash
.venv/bin/python board-game/tools/telegram.py gate2 <slug>
```
Then `advance --to awaiting_ship` and stop. The pipeline never publishes
anything itself; the owner's `pipeline_queue.py ship` is what makes a game shipped.

## The owner's replies

These are commands the owner runs; the Telegram messages contain them ready to
paste. Never run them on the owner's behalf.

```bash
.venv/bin/python board-game/tools/pipeline_queue.py ship   <slug>
.venv/bin/python board-game/tools/pipeline_queue.py reject <slug> --reason "..."
.venv/bin/python board-game/tools/pipeline_queue.py rework <slug> --reason "..."
```

A rejection reason lands in `board-game/TASTE.md` and is read by every future
ideation. It is the only signal in this pipeline that does not come from a
model, which is why it outranks everything an agent has learned on its own.

## Narrate it

`pipeline_queue.py` already narrates every state change to the owner's journal
channel. Your job is the half a state machine cannot produce: **why**. After
each action, add one entry:

```bash
.venv/bin/python board-game/tools/journal.py append <slug> --kind <kind> \
    --by <agent-or-tool> --title "<game name>" --summary "<one plain line>" \
    [--body "<verbatim detail>" | --body-file <path>]
```

What is worth an entry, by action:

| action | narrate |
|---|---|
| `propose` | what the ideator was going for, and what its novelty search actually turned up |
| `rules_gate` | the findings verbatim (`--body-file rules_check.json`), and what the rework changed |
| `brief` | the dimensions it chose, and every entry in `unstated_in_spec` — those are the places the spec ran out and somebody guessed |
| `draft` | what the draft looks like and anything that surprised the builder |
| `build` / `repair` | the gate findings verbatim (`--body-file .../gate.json`), then what the repair actually changed — not "fixed the overhang", but which number moved |
| `panel` | each lens's verdict line, verbatim |

Write it for a person who was not here. Include what went badly: a guess that
turned out wrong is the most useful line in the whole story, and nothing in
this pipeline ever reads the journal back, so there is nobody to impress.

Never summarise a checker's output into your own words when you could paste
it — the owner is trying to see what the machine actually said.

## Rules for you

- **Never edit a gate, a threshold, `bill.json`, or a brief to make something
  pass.** If a gate looks wrong, say so and stop. A pipeline that can relax its
  own acceptance criteria produces nothing worth having.
- **Never fabricate a stage.** If a build failed, the state stays where it is
  and the failure is reported. An idea that dies of a tooling fault is retried,
  not replaced — that is the whole reason the queue exists.
- Repair budget and state transitions belong to `pipeline_queue.py`. Do not track them
  in your own head, and do not work around a refusal.
- Report in one or two lines: what ran, what it produced, what is next.
