#!/usr/bin/env python3
"""journal.py — narrates what happens to an idea, to a Telegram channel of its
own, and to a local log file kept solely for `dashboard.py`.

    python3 board-game/tools/journal.py append <slug> --kind gate --by gate.py \\
        --summary "GATE FAIL — 3 findings" --body-file gate.json

Every idea generates a running story in the journal channel: who did what, what
they decided, what the checkers said verbatim, and what you said back. It is a
separate channel from the approval gates on purpose — the gate channel holds
the two messages that need you to press something, and burying those under
fifteen progress notes is how a gate stops being read.

**Nothing in the pipeline reads any of this.** `JOURNAL_LOG` below exists for
exactly one reader: `dashboard.py`, generating a page for the owner to look
at. No agent, no `improve.py`, no `audit.py` may open it — if you are adding
code to this pipeline and you are tempted to `open(JOURNAL_LOG)` from
anywhere other than `dashboard.py`, stop. That matters more than it sounds. A
log that feeds back into the system stops being a record of what happened and
becomes another surface to optimise — agents write for the reader they
expect, and the unflattering detail, the guess that turned out wrong, the
finding that was waved away, is exactly what disappears first. Keeping this
to one reader, who never talks back to the pipeline, is what keeps that
boundary free instead of a rule someone has to remember.

So: write plainly, include what went badly, and never round a failure up into
something tidier than it was.

Configure `TELEGRAM_CHAT_JOURNAL` in `.env` (a second chat or channel; the
same bot token works for both). Without it, entries print to stdout, which is
also how you read them before any bot exists. Either way, every entry is also
appended to `JOURNAL_LOG` (one JSON object per line, untruncated) for the
dashboard to read.

`pipeline_queue.py` narrates every state transition on its own, so the
skeleton is automatic. The interesting entries are the ones the driver and the
agents add: why an idea was proposed, what a brief had to guess at, what a
repair actually changed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[2]
JOURNAL_LOG = REPO_ROOT / "board-game" / ".journal_log.jsonl"

# Kept short and concrete on purpose — a vocabulary nobody can remember gets
# used as `note` for everything, and then the story stops being skimmable.
KINDS = {
    "proposed": "the idea was invented",
    "gate": "a deterministic checker ran",
    "rework": "the idea changed in response to something",
    "brief": "dimensions were chosen",
    "draft": "the first real geometry",
    "build": "the full build",
    "repair": "a repair round",
    "lens": "a review lens gave a verdict",
    "owner": "you decided something",
    "state": "the pipeline moved it",
    "note": "anything else worth remembering",
}

MAX_BODY = 2500


def record(slug: str, kind: str, by: str, summary: str,
           body: str, title: str, at: str) -> None:
    """Append one untruncated entry to `JOURNAL_LOG`, for `dashboard.py` only —
    see the module docstring before adding another reader."""
    JOURNAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "at": at, "slug": slug, "kind": kind, "by": by,
        "title": title or slug, "summary": summary.strip(), "body": body.strip(),
    })
    with JOURNAL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def append(slug: str, kind: str, by: str, summary: str,
           body: str = "", title: str = "") -> None:
    import telegram  # deferred: telegram owns the transport, journal owns the voice

    telegram.load_env()
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%H:%M")
    record(slug, kind, by, summary, body, title, now.isoformat())

    head = f"{title or slug} · {kind}\n{stamp} · {by}\n\n{summary.strip()}"
    if body.strip():
        detail = body.strip()
        if len(detail) > MAX_BODY:
            detail = detail[:MAX_BODY] + f"\n… [{len(detail) - MAX_BODY} more chars]"
        head += "\n\n" + detail

    chat = os.environ.get("TELEGRAM_CHAT_JOURNAL", "").strip()
    if not chat:
        print(f"--- journal ({slug}) ---\n{head}")
        return
    telegram.send(head, chat=chat)


def cmd_append(args) -> int:
    body = args.body or ""
    if args.body_file:
        source = Path(args.body_file)
        if source.is_file():
            text = source.read_text(encoding="utf-8", errors="ignore")
            body = (body + "\n\n" + text).strip() if body else text
    append(args.slug, args.kind, args.by, args.summary, body, args.title or "")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("append", help="narrate one event")
    p.add_argument("slug")
    p.add_argument("--kind", required=True, choices=sorted(KINDS))
    p.add_argument("--by", required=True,
                   help="who acted: an agent name, a tool name, or 'owner'")
    p.add_argument("--summary", required=True, help="one line, in plain words")
    p.add_argument("--title", help="the game's name, for the message header")
    p.add_argument("--body", help="optional detail, sent verbatim")
    p.add_argument("--body-file", help="file whose contents become the detail")
    p.set_defaults(fn=cmd_append)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
