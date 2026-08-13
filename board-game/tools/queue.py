#!/usr/bin/env python3
"""queue.py — the pipeline's state, and the only thing allowed to decide what
happens next.

    python3 board-game/tools/queue.py next          # what should run now
    python3 board-game/tools/queue.py list
    python3 board-game/tools/queue.py add <slug> --title "..."
    python3 board-game/tools/queue.py advance <slug> --to built --note "..."
    python3 board-game/tools/queue.py repair <slug>        # consume one round
    python3 board-game/tools/queue.py ship <slug>          # owner: gate 2 yes
    python3 board-game/tools/queue.py reject <slug> --reason "..."
    python3 board-game/tools/queue.py rework <slug> --reason "..."

An idea lives here across many turns. That is the change the whole rebuild
turns on: for fifteen turns an idea that died of an infrastructure fault was
replaced by a fresh one and nothing was ever finished. Now the unit of work is
an idea, not a turn, and an idea only leaves the queue by shipping or by being
killed for a stated reason.

Why this is Python and not instructions in a prompt: the repair budget lives
here. An agent that can read its own budget in its own prompt is an agent that
will negotiate with it. Same for state transitions — a stage is complete when
this file says so, not when a model reports success.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE = REPO_ROOT / "board-game" / "QUEUE.json"
IDEAS = REPO_ROOT / "board-game" / "ideas"
TASTE = REPO_ROOT / "board-game" / "TASTE.md"

# Two repair rounds, then arbitration. Not a technical ceiling — text2cad's
# evidence is that past two rounds the problem is usually the spec rather than
# the code, and more repair rounds spend effort at the wrong address.
REPAIR_BUDGET = 2

# state -> (what to run next, state it moves to on success)
# `None` action means the pipeline is waiting on the owner and this idea is
# skipped by `next` — which is exactly why a queue exists: one idea waiting on
# a human must never stall the others.
PIPELINE: dict[str, tuple[str | None, str]] = {
    "proposed":       ("rules_gate", "rules_ok"),
    "rules_ok":       ("brief", "briefed"),
    "briefed":        ("draft", "drafted"),
    "drafted":        ("owner_gate_1", "awaiting_owner"),
    "awaiting_owner": (None, "awaiting_owner"),
    "approved":       ("build", "built"),
    "built":          ("panel", "reviewed"),
    "reviewed":       ("owner_gate_2", "awaiting_ship"),
    "awaiting_ship":  (None, "awaiting_ship"),
    "repairing":      ("repair", "built"),
    "shipped":        (None, "shipped"),
    "killed":         (None, "killed"),
    "blocked":        (None, "blocked"),
}

# Ideas closest to shipping go first: finishing something beats starting
# something. `proposed` sits last so a backlog never crowds out a build.
PRIORITY = ["reviewed", "built", "repairing", "approved", "briefed",
            "rules_ok", "proposed"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load() -> dict:
    if not QUEUE.is_file():
        return {"ideas": {}}
    return json.loads(QUEUE.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def entry(data: dict, slug: str) -> dict:
    try:
        return data["ideas"][slug]
    except KeyError:
        raise SystemExit(f"no idea '{slug}' in the queue")


def log(item: dict, frm: str, to: str, note: str = "") -> None:
    item.setdefault("log", []).append(
        {"at": now(), "from": frm, "to": to, "note": note})


# ---------------------------------------------------------------------------

def cmd_add(args) -> int:
    data = load()
    if args.slug in data["ideas"]:
        raise SystemExit(f"'{args.slug}' is already in the queue")
    data["ideas"][args.slug] = {
        "slug": args.slug, "title": args.title or args.slug,
        "state": "proposed", "repairs_used": 0, "created": now(), "log": [],
    }
    (IDEAS / args.slug).mkdir(parents=True, exist_ok=True)
    save(data)
    print(f"added {args.slug} (proposed)")
    return 0


def cmd_advance(args) -> int:
    data = load()
    item = entry(data, args.slug)
    frm = item["state"]
    if args.to not in PIPELINE:
        raise SystemExit(f"unknown state '{args.to}'")
    item["state"] = args.to
    log(item, frm, args.to, args.note or "")
    save(data)
    print(f"{args.slug}: {frm} -> {args.to}")
    return 0


def cmd_repair(args) -> int:
    """Consume one repair round. Refuses past the budget — the caller is meant
    to escalate to arbitration, not to keep going."""
    data = load()
    item = entry(data, args.slug)
    used = int(item.get("repairs_used", 0))
    if used >= REPAIR_BUDGET:
        print(f"BUDGET EXHAUSTED {args.slug}: {used}/{REPAIR_BUDGET} repair "
              f"rounds spent — escalate to arbitration, do not repair again")
        return 1
    item["repairs_used"] = used + 1
    frm = item["state"]
    item["state"] = "repairing"
    log(item, frm, "repairing", f"repair round {used + 1}/{REPAIR_BUDGET}")
    save(data)
    print(f"{args.slug}: repair round {used + 1}/{REPAIR_BUDGET}")
    return 0


def cmd_ship(args) -> int:
    data = load()
    item = entry(data, args.slug)
    frm = item["state"]
    item["state"] = "shipped"
    item["shipped_at"] = now()
    log(item, frm, "shipped", "owner approved")
    save(data)
    print(f"{args.slug}: SHIPPED")
    return 0


def cmd_reject(args) -> int:
    """The owner said no. The reason is the single most valuable sentence in
    this pipeline: it is the only signal that comes from a human, and it goes
    into TASTE.md where every future ideation reads it."""
    data = load()
    item = entry(data, args.slug)
    frm = item["state"]
    item["state"] = "killed"
    item["kill_reason"] = args.reason
    log(item, frm, "killed", args.reason)
    save(data)

    if not TASTE.is_file():
        TASTE.write_text(
            "# TASTE — the owner's own words\n\n"
            "Every line here is a rejection reason, verbatim. This is the only\n"
            "signal in the pipeline that does not come from a model, so it\n"
            "outranks every heuristic an agent has learned on its own.\n"
            "`board-game-ideator` reads this file before it invents anything.\n\n",
            encoding="utf-8")
    with TASTE.open("a", encoding="utf-8") as fh:
        fh.write(f"- REJECTED **{item.get('title', args.slug)}** "
                 f"({args.slug}): {args.reason}\n")
    print(f"{args.slug}: killed — reason recorded in TASTE.md")
    return 0


def cmd_rework(args) -> int:
    data = load()
    item = entry(data, args.slug)
    frm = item["state"]
    item["state"] = "proposed"
    item["rework_reason"] = args.reason
    log(item, frm, "proposed", f"owner asked for a rules change: {args.reason}")
    save(data)
    print(f"{args.slug}: back to proposed for rework")
    return 0


def cmd_next(args) -> int:
    """Print the one thing that should happen now, as JSON. The driver reads
    this and does exactly that — it does not get to pick."""
    data = load()
    for state in PRIORITY:
        for slug, item in sorted(data["ideas"].items()):
            if item["state"] != state:
                continue
            action, to = PIPELINE[state]
            if action is None:
                continue
            print(json.dumps({
                "slug": slug, "title": item.get("title", slug),
                "state": state, "action": action, "next_state": to,
                "repairs_used": item.get("repairs_used", 0),
                "repair_budget": REPAIR_BUDGET,
                "dir": str(IDEAS / slug),
            }, indent=2))
            return 0
    waiting = [s for s, i in data["ideas"].items()
               if i["state"] in ("awaiting_owner", "awaiting_ship")]
    print(json.dumps({"action": "propose",
                      "reason": ("every idea in the queue is waiting on the owner"
                                 if waiting else "the queue has nothing to advance"),
                      "waiting_on_owner": waiting}, indent=2))
    return 0


def cmd_list(args) -> int:
    data = load()
    if not data["ideas"]:
        print("queue is empty")
        return 0
    width = max(len(s) for s in data["ideas"])
    for slug, item in sorted(data["ideas"].items(),
                             key=lambda kv: PRIORITY.index(kv[1]["state"])
                             if kv[1]["state"] in PRIORITY else 99):
        repairs = item.get("repairs_used", 0)
        tail = f"  repairs {repairs}/{REPAIR_BUDGET}" if repairs else ""
        note = f"  — {item['kill_reason']}" if item.get("kill_reason") else ""
        print(f"  {slug:<{width}}  {item['state']:<14}{tail}{note}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add"); p.add_argument("slug"); p.add_argument("--title")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("advance"); p.add_argument("slug")
    p.add_argument("--to", required=True); p.add_argument("--note")
    p.set_defaults(fn=cmd_advance)
    p = sub.add_parser("repair"); p.add_argument("slug"); p.set_defaults(fn=cmd_repair)
    p = sub.add_parser("ship"); p.add_argument("slug"); p.set_defaults(fn=cmd_ship)
    p = sub.add_parser("reject"); p.add_argument("slug")
    p.add_argument("--reason", required=True); p.set_defaults(fn=cmd_reject)
    p = sub.add_parser("rework"); p.add_argument("slug")
    p.add_argument("--reason", required=True); p.set_defaults(fn=cmd_rework)
    sub.add_parser("next").set_defaults(fn=cmd_next)
    sub.add_parser("list").set_defaults(fn=cmd_list)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
