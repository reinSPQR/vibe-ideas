# vibe-ideas

An autonomous pipeline that invents physical board games, designs every piece
as CadQuery code, prints-checks them against a real bed, and carries the ones a
human approves onto a storefront. One `/bg` call advances exactly one idea by
exactly one step; the queue decides which idea and which step, so the loop can
be driven by a cron, a `/loop`, or a person typing `/bg` when they feel like it.

```
 IDEA ─────────────────────────────────────────────────────────────────
   board-game-ideator                        TASTE.md
   concept + COMPLETE rules + bill    ◀── (the owner's own rejection
   + art direction, in form language       reasons, verbatim)
        │
        ▼
 ┌────────────────────────────┐
 │ ① RULES GATE  (no LLM)     │  rules_check.py: reachable ending, real
 │ then board-game-lens-rules │  decisions, player count, length
 └────────┬───────────────────┘  the lens: is it worth playing at all?
          ▼
 ┌────────────────────────────┐
 │ ② BRIEF                    │  every dimension in mm, every interface
 │ board-game-brief-writer    │  between pieces, the print plan, tiling
 └────────┬───────────────────┘  of anything bigger than the bed
          ▼
 ┌────────────────────────────┐
 │ ③ DRAFT  (fast + honest)   │──▶ renders ──▶ 📱 OWNER GATE 1
 │ board-game-builder         │                approve / rework / reject
 └────────┬───────────────────┘
          ▼  approved renders freeze into reference/ — a visual contract
 ┌────────────────────────────┐
 │ ④ BUILD                    │  one named assembly child per component,
 │ board-game-builder         │  fit_checks.py written from the brief's
 └────────┬───────────────────┘  interfaces
          ▼
 ┌────────────────────────────┐
 │ ⑤ GATE  (no LLM)           │  watertight, one body, bed fit, overhangs,
 │ gate.py → gate.json        │  bridges, bill match, piece-vs-piece
 └────────┬───────────────────┘  interference, fit_checks.py
          ▼
 ┌────────────────────────────┐
 │ ⑥ PANEL — 3 lenses, blind  │  printability │ fidelity │ playability
 │ to each other              │  fidelity compares view-by-view against
 └────────┬───────────────────┘  reference/
          ▼
 ┌────────────────────────────┐
 │ ⑦ REPAIR — budget of 2     │──▶ exhausted → ARBITRATION: propose a
 │ re-gate, re-run failed lens│    brief amendment, ask the owner, stop
 └────────┬───────────────────┘
          ▼ all green
        📱 OWNER GATE 2 — ship / reject
          ▼
 ┌────────────────────────────┐
 │ ⑧ PUBLISH  (optional)      │  the whole project folder + a generated
 │ publish.py                 │  RULES.md, as a DRAFT design on Panda
 └────────────────────────────┘  Social. The public flip stays human.
```

## The queue is the pipeline

`board-game/QUEUE.json` holds every idea and its state; `pipeline_queue.py` is
the only thing allowed to move one. An agent cannot negotiate with its own
repair budget because the budget lives in Python, not in a prompt, and a stage
is complete when the queue says so — not when a model reports success.

```bash
.venv/bin/python board-game/tools/pipeline_queue.py next    # what runs now (and claims it)
.venv/bin/python board-game/tools/pipeline_queue.py list    # where everything is
```

Two drivers can run at once: every read-modify-write takes a file lock, and
`next` hands out a *claim* — a lease with an expiry — so a tick that lands
mid-step is told to wait instead of spawning a second agent onto the same
files. A driver that dies releases its idea when the lease lapses.

The two owner gates arrive as Telegram messages with buttons. Ship, and a
📦 Publish button follows.

## Loops

- **In-run:** the build loop, the repair loop (budget 2), and a re-run of only
  the lenses that failed.
- **Across runs:** every rejection reason is appended verbatim to
  `board-game/TASTE.md`, which the ideator reads before it invents anything.
  It is the only signal in the pipeline that does not come from a model, which
  is why it outranks everything an agent has learned on its own.
- **On the pipeline itself:** `PAIN_POINTS.md` collects what each step found
  awkward, `lessons.md` holds rules that graduated from advice into code, and
  `audit.py` + the `board-game-auditor` agent check the loop is not just
  getting better at its own metrics (`INTEGRITY.md`). `improve.py` runs the
  self-improvement session; it is forbidden from touching `ideas/` and
  `history/`.

## Layout

| Path | What |
|---|---|
| `.claude/commands/bg.md` | the driver — one step per invocation |
| `.claude/agents/` | ideator, brief-writer, builder, four lenses, auditor |
| `board-game/tools/` | the queue, the gates, Telegram, the journal, publish |
| `board-game/blocks/` | reusable CAD blocks the builder composes from first |
| `board-game/ideas/<slug>/` | one game: idea.json, brief, draft, project, verdicts |
| `cadcode/` | the CAD skill the builder drives (own LICENSE) |
| `evaluate-cad-reconstruction/` | separate skill: scoring CAD reconstructions |

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python cadquery trimesh numpy manifold3d pillow matplotlib
cp .env.example .env        # Telegram bot token + chat ids
```

Then drive it:

```bash
/bg                       # one step, in Claude Code
/loop 10m /bg             # or let it run
scripts/start-dashboard.sh  # queue + journal + 3D viewer in a browser
```

Requires the `claude` CLI, and the `cadcode` skill in this repo (the builder
calls `cadcode/scripts/cad` and `cadcode/scripts/review` directly). The gate
targets a Bambu Lab P2S — 256mm nominal, minus a 5mm margin per side — via
`BED_X_MM` / `BED_Y_MM` / `BED_Z_MM` in `gate.py`. Change those for another
printer.

## Publishing needs a second, private repo

`board-game/tools/publish.py` imports a shipped game into Panda Social as a
draft design. It drives
`bin/publishdesign`, a Go CLI that must be **compiled against a checkout of
`panda-social-backend`** — a private repo — because it calls that backend's own
`services.ImportDesign`, the same function `POST /designs/import` runs. That is
deliberate: the CDN snapshot, the `_tree.json` the viewer reads, the GLB, the
thumbnails, `root_id` and the unique slug all come from the backend's code
rather than a second implementation that drifts out of sync with it.

Without that repo, everything up to and including OWNER GATE 2 works; only the
last box in the diagram does not. Nothing else in the pipeline imports it.

```bash
board-game/tools/publishdesign/build.sh [path/to/panda-social-backend]
.venv/bin/python board-game/tools/publish.py <slug> --dry-run
```

`.env` also needs `PANDA_OWNER_ID`, `PANDA_BACKEND_DIR` and
`GOOGLE_APPLICATION_CREDENTIALS` for that half. Mongo and GCS settings are not
duplicated here — the CLI runs with the backend checkout as its working
directory and reads that repo's own `.env`.

## What is not in git

Anything a clone can re-derive: exported meshes (`*.stl`, `*.step`,
`*.step.json`), part renders, `build/`, and the deterministic check outputs
(`rules_check.json`, `ergonomics_check.json`). Regenerate them from the source
that is committed:

```bash
.venv/bin/python cadcode/scripts/cad    board-game/ideas/<slug>/project --out-dir board-game/ideas/<slug>/project/build
.venv/bin/python cadcode/scripts/review board-game/ideas/<slug>/project
.venv/bin/python board-game/tools/gate.py board-game/ideas/<slug>/project --bill board-game/ideas/<slug>/project/bill.json
```

What stays is what no clone can re-derive: the source, `gate.json` (a
measurement over one specific source hash), the panel's verdicts, and the two
renders a human actually looked at and approved — `_assembled.png` and
`_qa.png`, under both `reference/` (the approved draft) and
`project/<slug>_review/` (what was built).

`board-game/history/` is the archive of the older turn-based loop, kept out of
the repo; `contact_sheet.py` and `score_build.py` are its tools and read
nothing the current pipeline writes.
