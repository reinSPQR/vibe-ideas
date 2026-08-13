#!/usr/bin/env python3
"""telegram.py — the owner's two approval gates, and the two escalations.

    python3 board-game/tools/telegram.py gate1       <slug>
    python3 board-game/tools/telegram.py gate2       <slug>
    python3 board-game/tools/telegram.py arbitration <slug>
    python3 board-game/tools/telegram.py stuck       <slug>
    python3 board-game/tools/telegram.py heartbeat
    python3 board-game/tools/telegram.py watchdog --max-hours 28

Every message carries the reply commands ready to paste. There is no webhook
and no polling: the owner answers by running one line, which means this whole
channel is a `curl` and a file, with nothing to keep alive.

Without TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_DM the message is printed to stdout
instead of being sent. That is a deliberate fallback rather than a silent
skip — the gate still happens, it just happens in the terminal, and the
pipeline is usable before anyone sets up a bot.

Reads .env from the repo root if present.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IDEAS = REPO_ROOT / "board-game" / "ideas"
HEARTBEAT = REPO_ROOT / "board-game" / ".heartbeat"
PY = ".venv/bin/python"
Q = "board-game/tools/pipeline_queue.py"


def load_env() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


def creds() -> tuple[str, str]:
    return (os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
            os.environ.get("TELEGRAM_CHAT_DM", "").strip())


def send(text: str, photo: Path | None = None) -> None:
    token, chat = creds()
    if not (token and chat):
        print("--- telegram not configured; the gate is here instead ---")
        if photo:
            print(f"[render] {photo}")
        print(text)
        return
    if photo and photo.is_file():
        subprocess.run(["curl", "-s", "-o", "/dev/null",
                        f"https://api.telegram.org/bot{token}/sendPhoto",
                        "-F", f"chat_id={chat}", "-F", f"photo=@{photo}",
                        "-F", f"caption={text[:1024]}"], timeout=120)
        if len(text) > 1024:
            send_text_only(token, chat, text[1024:])
    else:
        send_text_only(token, chat, text)
    print(f"sent ({len(text)} chars{', with render' if photo else ''})")


def send_text_only(token: str, chat: str, text: str) -> None:
    for chunk in (text[i:i + 3500] for i in range(0, len(text), 3500)):
        subprocess.run(["curl", "-s", "-o", "/dev/null",
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        "-d", f"chat_id={chat}",
                        "--data-urlencode", f"text={chunk}"], timeout=60)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def find_hero(slug: str) -> Path | None:
    """The cover render cadcode's review pass writes (`_assembled.png`), or
    any hero we have. Renders are the entire point of gate 1 — the owner is
    judging an object, not a paragraph."""
    home = IDEAS / slug
    for pattern in ("**/_assembled.png", "**/cover.png", "**/*_qa.png"):
        found = sorted(home.glob(pattern))
        if found:
            return found[0]
    return None


def rules_summary(idea: dict) -> str:
    """One screen. If it does not fit on a phone it will not be read, and a
    gate nobody reads is a gate that always says yes."""
    players = idea.get("players") or {}
    lines = [
        idea.get("concept", "").strip(),
        "",
        f"{players.get('min', '?')}-{players.get('max', '?')} players · "
        f"~{idea.get('playtime_min', '?')} min",
        "",
        "TURN:",
    ]
    for step in (idea.get("rules") or {}).get("turn") or []:
        lines.append(f"  · {step.get('text', '')}")
    win = (idea.get("rules") or {}).get("win") or {}
    lines += ["", f"WIN: {win.get('text', '?')}", "", "BOX:"]
    for c in idea.get("components") or []:
        lines.append(f"  {c.get('qty', '?')}x {c.get('name', '?')}")
    return "\n".join(lines)


def cmd_gate1(args) -> int:
    slug = args.slug
    idea = read_json(IDEAS / slug / "idea.json")
    title = idea.get("title", slug)
    text = (f"BOARD GAME — worth building?\n"
            f"{title} ({slug})\n\n"
            f"{rules_summary(idea)}\n\n"
            f"This is a real CadQuery draft, not an illustration. If you say "
            f"yes, the final build is held to matching it.\n\n"
            f"YES:  {PY} {Q} approve {slug}\n"
            f"NO:   {PY} {Q} reject {slug} --reason \"...\"\n"
            f"RULES:{PY} {Q} rework {slug} --reason \"...\"")
    send(text, find_hero(slug))
    return 0


def cmd_gate2(args) -> int:
    slug = args.slug
    idea = read_json(IDEAS / slug / "idea.json")
    gate = read_json(IDEAS / slug / "project" / "gate.json")
    verdicts = []
    for lens in ("printability", "fidelity", "playability"):
        path = IDEAS / slug / f"review_{lens}.md"
        first = (path.read_text(encoding="utf-8").splitlines() or [""])[0] \
            if path.is_file() else "no verdict"
        verdicts.append(f"  {lens}: {first.replace('Verdict:', '').strip()}")

    parts = gate.get("part_count", "?")
    shapes = gate.get("distinct_shapes", "?")
    sliced = [v for v in (gate.get("slice") or {}).values() if v.get("print_min")]
    hours = sum(v["print_min"] for v in sliced) / 60.0 if sliced else None

    text = (f"BOARD GAME — ship it?\n"
            f"{idea.get('title', slug)} ({slug})\n\n"
            f"GATE PASS · {parts} pieces, {shapes} distinct shapes"
            + (f" · ~{hours:.1f}h of printing\n" if hours else "\n")
            + "\n".join(verdicts)
            + f"\n\nFiles: board-game/ideas/{slug}/project/\n\n"
              f"SHIP: {PY} {Q} ship {slug}\n"
              f"NO:   {PY} {Q} reject {slug} --reason \"...\"")
    send(text, find_hero(slug))
    return 0


def cmd_arbitration(args) -> int:
    slug = args.slug
    proposal = read_json(IDEAS / slug / "brief_proposed.json")
    amendments = proposal.get("amendments") or []
    text = (f"ARBITRATION — {slug}\n\n"
            f"The repair budget is spent and what is left looks like a spec "
            f"conflict, not a build defect: the brief is asking for things "
            f"that cannot all be true at once.\n\nProposed changes:\n"
            + "\n".join(f"  · {a}" for a in amendments)
            + f"\n\nDetails: board-game/ideas/{slug}/brief_proposed.json\n\n"
              f"APPLY:  {PY} {Q} amend {slug}\n"
              f"DROP:   rm board-game/ideas/{slug}/brief_proposed.json")
    send(text)
    return 0


def cmd_stuck(args) -> int:
    slug = args.slug
    gate = read_json(IDEAS / slug / "project" / "gate.json")
    fails = gate.get("fails") or ["(no gate report)"]
    text = (f"STUCK — {slug}\n\n"
            f"Repair budget spent and this is not a spec conflict, so it needs "
            f"a look. Still failing:\n"
            + "\n".join(f"  · {f}" for f in fails[:10])
            + f"\n\n{PY} {Q} list")
    send(text)
    return 0


def cmd_heartbeat(args) -> int:
    HEARTBEAT.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    print(f"heartbeat {HEARTBEAT}")
    return 0


def cmd_watchdog(args) -> int:
    """Silence has to be alarmable. A pipeline that stops running looks exactly
    like a pipeline with nothing to do, until you check a month later."""
    if not HEARTBEAT.is_file():
        send("WATCHDOG — the board-game pipeline has never checked in.")
        return 1
    last = datetime.fromisoformat(HEARTBEAT.read_text(encoding="utf-8").strip())
    stale = datetime.now(timezone.utc) - last
    if stale > timedelta(hours=args.max_hours):
        send(f"WATCHDOG — the board-game pipeline has been silent for "
             f"{stale.total_seconds() / 3600:.0f}h (last {last.isoformat()}).")
        return 1
    print(f"ok, last heartbeat {stale.total_seconds() / 3600:.1f}h ago")
    return 0


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("gate1", cmd_gate1), ("gate2", cmd_gate2),
                     ("arbitration", cmd_arbitration), ("stuck", cmd_stuck)):
        p = sub.add_parser(name)
        p.add_argument("slug")
        p.set_defaults(fn=fn)
    sub.add_parser("heartbeat").set_defaults(fn=cmd_heartbeat)
    p = sub.add_parser("watchdog")
    p.add_argument("--max-hours", type=float, default=28.0)
    p.set_defaults(fn=cmd_watchdog)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
