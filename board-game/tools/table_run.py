"""table_run.py — the agent-played half of gate R1c. One model per seat.

`playtest.py` plays a game several thousand times with scripted policies and
measures what a policy can measure: whether it ends, whether the first seat
wins, whether looking ahead helps. Three things stay out of its reach, and all
three need somebody who is trying to win and can say what that was like:

1. Where the rules failed to say, found by running into it with a plan rather
   than by reading the prose with a checklist.
2. Which turns had no decision in them. A policy always picks something; only
   a player can report that seven options were the same option.
3. Whether the game got smaller. A game dies the evening somebody works it
   out, and the only witness to that is a player who was there the first time
   and had to think.

This file is the harness that makes those three measurable. It is deliberately
NOT an agent. The loop that renders a position, sends it to the seat whose
turn it is, reads back one index, and applies it, is completely deterministic,
so it is written as code. That is not a style preference. An LLM driving this
loop can play a turn for a player who is slow, quietly answer a rules question
it should have recorded as a finding, show one seat what another seat is
holding, or run the game again because the first one was dull. Every one of
those was a written prohibition in an earlier design, and a prohibition is a
thing you hope holds. Here they are not prohibited, they are absent: this
process has no way to express them.

What the players cannot do is worth stating as plainly. A seat is a chat
conversation and nothing else. It has no tools, no filesystem, and no way to
reach `playtest.json`, the engine, or another seat's messages. It chooses by
index out of a list the engine generated, so it cannot make an illegal move or
misremember the board, and it is shown `observation(state, seat)` and never
the state, so in a hidden-information game it cannot see what it should not.

Two backends, selected with --driver, because which one to build on is an open
question and the honest way to settle it is to run both over the same games
and compare what they cost and what they found:

  chat  one HTTPS round trip per decision, urllib only, no dependencies. The
        whole conversation is resent every turn, which is what makes prompt
        caching worth measuring rather than assuming.
  sdk   claude_agent_sdk.ClaudeSDKClient, one persistent session per seat.

Both read PLAYTEST_BASE_URL, PLAYTEST_API_KEY and PLAYTEST_MODEL, so the same
endpoint serves both and the comparison is between the drivers rather than
between two providers.

Usage:

    export PLAYTEST_BASE_URL=https://your-endpoint
    export PLAYTEST_API_KEY=...
    export PLAYTEST_MODEL=...
    .venv/bin/python board-game/tools/table_run.py board-game/ideas/deep-claim \
        --schedule 4:3,2:2 --driver chat --wire anthropic

Writes one session per game to <idea_dir>/playtest/table/<label>.json, in the
same format `playtest.py table` writes, so any game replays from its seed and
recorded choices and an engine edited mid-run is caught rather than absorbed.
Writes the run summary to <idea_dir>/playtest/table/run_<driver>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import playtest  # noqa: E402  (path is set immediately above)

# A reply that does not parse is re-asked this many times before the run stops.
# Two is deliberate: one retry absorbs a model that wrapped its answer in
# prose, and a seat that cannot produce `CHOICE <n>` twice running is a broken
# configuration, not a bad turn, and should fail loudly rather than be papered
# over with a policy move that the report would then read as a player's.
MAX_REPLY_RETRIES = 2
REQUEST_TIMEOUT = 180.0
DEFAULT_MAX_TOKENS = 1024
ANTHROPIC_VERSION = "2023-06-01"

PLAYER_BRIEF = Path(__file__).resolve().parents[2] / ".claude" / "agents" \
    / "board-game-player.md"

BREAKER_BRIEF = """
# Your job at this table is different

You are not here to enjoy this game. You are here to break it.

Find a line that wins regardless of what the others do. Once you have it, run
it every game, and say in your debrief which turn you knew it was working. If
you cannot find one after several games, say that too, clearly, because a game
that survives somebody actively trying to kill it is the good outcome and it
is worth as much as the kill.

A table of agreeable players will not break a game that a motivated opponent
breaks on the second evening. You are the second evening.
""".strip()


# ---------------------------------------------------------------------------
# The brief a seat is given
# ---------------------------------------------------------------------------

def strip_frontmatter(text: str) -> str:
    """The player brief lives in the agent file so there is one copy of it."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def render_rules(idea: dict) -> str:
    """The rulebook, with the same step ids the rest of the pipeline uses.

    A player who wants to raise a rules question has to be able to point at
    the step that defeated it, and `rules:turn[5]` only means something if the
    numbering it saw is the numbering `rules_check.py` and the engine use.
    """
    out = [f"# {idea.get('title', idea.get('slug', '?'))}", "",
           idea.get("concept", ""), ""]
    players = idea.get("players") or {}
    out.append(f"Players: {players.get('min', '?')} to {players.get('max', '?')}. "
               f"Stated playtime: {idea.get('playtime_min', '?')} minutes.")
    out.append("")
    out.append("## Components")
    for comp in idea.get("components") or []:
        out.append(f"- {comp.get('name', '?')} x{comp.get('qty', '?')}: "
                   f"{comp.get('desc', '')}")
    out.append("")
    out.append("## Rules")
    for phase, body in (idea.get("rules") or {}).items():
        out.append(f"### {phase}")
        # Phases are lists of steps, except the ones that are a single clause
        # (`win` usually is). Both shapes get an id, because a player pointing
        # at `rules:win` has to be able to point at it the same way the engine
        # and rules_check.py do.
        if isinstance(body, list):
            for i, step in enumerate(body):
                text = step.get("text", "") if isinstance(step, dict) else step
                out.append(f"rules:{phase}[{i}]  {text}")
        elif isinstance(body, dict):
            text = body.get("text")
            out.append(f"rules:{phase}  "
                       + (text if text else json.dumps(body, indent=1)))
        else:
            out.append(f"rules:{phase}  {body}")
        out.append("")
    return "\n".join(out)


def seat_system_prompt(brief: str, rules: str, seat: int, seats: int,
                       breaker: bool) -> str:
    """Brief plus rulebook, both static for the whole run.

    They go in the system prompt rather than in the first turn's message
    because a player at a table has the rulebook beside it the whole evening,
    not recited once and taken away. That it is also the only large block that
    never changes, and so the only one a prompt cache can hold, is a happy
    coincidence and not the reason.
    """
    parts = [brief]
    if breaker:
        parts.append(BREAKER_BRIEF)
    parts.append(f"# You are seat {seat} of {seats}\n\n"
                 f"Seat numbers are stable for the whole run. When the seat "
                 f"count changes between games you keep your seat number and "
                 f"everything you have learned.")
    parts.append("# The rules of this game\n\n" + rules)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class Backend:
    name = "?"

    async def open_seat(self, key: str, system: str) -> None:
        raise NotImplementedError

    async def ask(self, key: str, text: str) -> tuple:
        """-> (reply_text, usage dict with in/out/cached keys)"""
        raise NotImplementedError

    async def close(self) -> None:
        return None


class ChatBackend(Backend):
    """One round trip per decision, whole history resent each time.

    Stateless on the wire and therefore trivially auditable: every byte a seat
    has ever been shown is in `self.history[key]` and gets written to the run
    file, so a reader can check for themselves that no seat saw another seat's
    observation.
    """

    def __init__(self, base_url: str, api_key: str, model: str, wire: str,
                 max_tokens: int, cache: bool):
        self.name = f"chat/{wire}" + ("/cached" if cache else "")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.wire = wire
        self.max_tokens = max_tokens
        self.cache = cache
        self.system: dict = {}
        self.history: dict = {}

    async def open_seat(self, key: str, system: str) -> None:
        self.system[key] = system
        self.history[key] = []

    def _body(self, key: str) -> tuple:
        system, messages = self.system[key], self.history[key]
        if self.wire == "openai":
            return (f"{self.base_url}/v1/chat/completions",
                    {"Authorization": f"Bearer {self.api_key}",
                     "content-type": "application/json"},
                    {"model": self.model, "max_tokens": self.max_tokens,
                     "messages": [{"role": "system", "content": system}]
                                 + messages})
        block = {"type": "text", "text": system}
        if self.cache:
            # The brief and the rulebook never change for the whole run, so
            # this one marker is the difference between paying for the
            # rulebook once and paying for it on every decision.
            block["cache_control"] = {"type": "ephemeral"}
        return (f"{self.base_url}/v1/messages",
                {"x-api-key": self.api_key,
                 "authorization": f"Bearer {self.api_key}",
                 "anthropic-version": ANTHROPIC_VERSION,
                 "content-type": "application/json"},
                {"model": self.model, "max_tokens": self.max_tokens,
                 "system": [block], "messages": messages})

    def _post(self, url: str, headers: dict, payload: dict) -> dict:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise RuntimeError(f"{exc.code} from {url}: {detail}") from None

    async def ask(self, key: str, text: str) -> tuple:
        self.history[key].append({"role": "user", "content": text})
        url, headers, payload = self._body(key)
        data = await asyncio.to_thread(self._post, url, headers, payload)
        if self.wire == "openai":
            reply = data["choices"][0]["message"]["content"] or ""
            raw = data.get("usage") or {}
            usage = {"in": raw.get("prompt_tokens", 0),
                     "out": raw.get("completion_tokens", 0),
                     "cached": (raw.get("prompt_tokens_details")
                                or {}).get("cached_tokens", 0)}
        else:
            reply = "".join(b.get("text", "") for b in data.get("content", [])
                            if b.get("type") == "text")
            raw = data.get("usage") or {}
            usage = {"in": raw.get("input_tokens", 0),
                     "out": raw.get("output_tokens", 0),
                     "cached": raw.get("cache_read_input_tokens", 0),
                     "cache_write": raw.get("cache_creation_input_tokens", 0)}
        self.history[key].append({"role": "assistant", "content": reply})
        return reply, usage


class SdkBackend(Backend):
    """One persistent ClaudeSDKClient session per seat.

    The SDK manages the conversation, prompt caching and context compaction
    itself, which is exactly the work ChatBackend leaves to us. Whether that
    management is worth a dependency and an Anthropic-format endpoint is the
    question this driver exists to answer, so both are wired the same way and
    the numbers decide.
    """

    name = "sdk"

    def __init__(self, model: str, max_tokens: int):
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            raise SystemExit(
                "TABLE ERROR --driver sdk needs the Agent SDK: "
                "`.venv/bin/pip install claude-agent-sdk`. It reads "
                "ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN, which this "
                "driver sets from PLAYTEST_BASE_URL and PLAYTEST_API_KEY, and "
                "the endpoint must speak the Anthropic Messages format; an "
                "OpenAI-compatible one will not do. Use --driver chat "
                "--wire openai for that.") from None
        self._options_cls = ClaudeAgentOptions
        self._client_cls = ClaudeSDKClient
        self.model = model
        self.max_tokens = max_tokens
        self.clients: dict = {}

    async def open_seat(self, key: str, system: str) -> None:
        options = self._options_cls(
            model=self.model,
            system_prompt=system,
            allowed_tools=[],
            permission_mode="default",
        )
        client = self._client_cls(options=options)
        await client.connect()
        self.clients[key] = client

    async def ask(self, key: str, text: str) -> tuple:
        client = self.clients[key]
        await client.query(text)
        chunks, usage = [], {"in": 0, "out": 0, "cached": 0}
        async for message in client.receive_response():
            for block in getattr(message, "content", None) or []:
                if hasattr(block, "text"):
                    chunks.append(block.text)
            raw = getattr(message, "usage", None)
            if isinstance(raw, dict):
                usage = {"in": raw.get("input_tokens", 0),
                         "out": raw.get("output_tokens", 0),
                         "cached": raw.get("cache_read_input_tokens", 0),
                         "cache_write": raw.get("cache_creation_input_tokens", 0)}
        return "".join(chunks), usage

    async def close(self) -> None:
        for client in self.clients.values():
            disconnect = getattr(client, "disconnect", None)
            if disconnect is not None:
                await disconnect()


# ---------------------------------------------------------------------------
# Reading a reply
# ---------------------------------------------------------------------------

CHOICE_RE = re.compile(r"^\s*CHOICE\s+(\d+)\s*$", re.M)
WHY_RE = re.compile(r"^\s*WHY\s+(.+)$", re.M)
ARBITRARY_RE = re.compile(r"^\s*ARBITRARY\s+(yes|no)\s*$", re.M | re.I)
QUESTION_RE = re.compile(r"^\s*RULES QUESTION\s+(.+)$", re.M)
NOTE_RE = re.compile(r"^\s*NOTE\s+(.+)$", re.M)


def parse_reply(text: str, n_moves: int) -> dict | None:
    """None when the reply cannot be read as a move.

    Deliberately strict about CHOICE and forgiving about everything else. A
    missing WHY costs one line of the report; a CHOICE guessed out of prose
    costs the integrity of the session file, because the recorded index is
    what the whole game replays from.
    """
    match = CHOICE_RE.search(text)
    if not match:
        return None
    choice = int(match.group(1))
    if not 0 <= choice < n_moves:
        return None
    why = WHY_RE.search(text)
    arb = ARBITRARY_RE.search(text)
    return {
        "choice": choice,
        "why": why.group(1).strip() if why else "",
        "arbitrary": bool(arb and arb.group(1).lower() == "yes"),
        "question": [m.strip() for m in QUESTION_RE.findall(text)],
        "note": [m.strip() for m in NOTE_RE.findall(text)],
    }


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

class Run:
    def __init__(self, eng, idea_dir: Path, backend: Backend, compact: bool):
        self.eng = eng
        self.idea_dir = idea_dir
        self.backend = backend
        self.compact = compact
        self.usage = {"in": 0, "out": 0, "cached": 0, "cache_write": 0,
                      "calls": 0}
        self.open_seats: set = set()
        self.questions: list = []
        self.debriefs: list = []
        self.games: list = []
        self.sent: dict = {}

    def _bill(self, usage: dict) -> None:
        for key in ("in", "out", "cached", "cache_write"):
            self.usage[key] += usage.get(key, 0)
        self.usage["calls"] += 1

    async def ensure_seat(self, seat: int, system: str) -> None:
        key = f"seat{seat}"
        if key not in self.open_seats:
            await self.backend.open_seat(key, system)
            self.open_seats.add(key)

    async def ask_seat(self, seat: int, text: str) -> str:
        self.sent.setdefault(seat, []).append(text)
        reply, usage = await self.backend.ask(f"seat{seat}", text)
        self._bill(usage)
        return reply

    def leaked_seats(self) -> list:
        """Was any seat ever sent a position addressed to a different seat?

        Routing is done by code here, so this should always come back empty.
        That is exactly why it is worth checking: one misrouted block in a
        hidden-information game destroys the run's value and leaves no trace
        anybody would notice afterwards, and a claim of "structurally
        impossible" is worth more when something verifies it every run.
        """
        bad = set()
        for seat, texts in self.sent.items():
            for text in texts:
                for other in re.findall(r"^YOU ARE seat (\d+)", text, re.M):
                    if int(other) != seat:
                        bad.add(f"seat {seat} was sent a block for seat {other}")
        return sorted(bad)

    async def play_game(self, seats: int, seed: int, label: str,
                        systems: dict, game_no: int) -> dict:
        eng = self.eng
        session = {
            "slug": getattr(eng, "SLUG", self.idea_dir.name),
            "idea_dir": str(self.idea_dir),
            "engine": str(self.idea_dir / "playtest" / "engine.py"),
            "seats": seats, "seed": seed, "scripted": {},
            "agent_turns": 0, "finish_with": "greedy",
            "seed_blind": playtest.seed_blind(eng, seats),
            "driver": self.backend.name,
            "handed_over_at": None, "moves": [],
        }
        state, rng = playtest.replay(eng, session)
        last_seen = {s: 0 for s in range(seats)}
        stuck = False

        for seat in range(seats):
            await self.ensure_seat(seat, systems[seat])

        while not eng.is_over(state):
            moves = eng.legal_moves(state)
            if not moves:
                stuck = True
                break
            seat = int(eng.player_to_move(state))
            block = "\n".join(
                playtest.played_lines(session, last_seen[seat])
                + [playtest.render_table(eng, session, state, label,
                                         self.compact)])
            parsed = None
            for attempt in range(MAX_REPLY_RETRIES + 1):
                prompt = block if attempt == 0 else (
                    f"That reply had no readable `CHOICE <n>` with n between 0 "
                    f"and {len(moves) - 1}. Send only the lines the brief asks "
                    f"for, starting with CHOICE.")
                parsed = parse_reply(await self.ask_seat(seat, prompt),
                                     len(moves))
                if parsed:
                    break
            if not parsed:
                raise SystemExit(
                    f"TABLE ERROR seat {seat} could not produce a readable "
                    f"CHOICE after {MAX_REPLY_RETRIES + 1} attempts in game "
                    f"{label}. Fix the seat or the brief; do not let a policy "
                    f"finish this game and call the result a player's.")

            for q in parsed["question"]:
                self.questions.append({"game": label, "seat": seat,
                                       "turn": len(session["moves"]),
                                       "text": q})
            session["moves"].append({
                "seat": seat, "choice": parsed["choice"],
                "move": str(moves[parsed["choice"]]), "by": "player",
                "why": parsed["why"], "arbitrary": parsed["arbitrary"],
                "note": parsed["note"] or None,
            })
            state = eng.apply_move(state, moves[parsed["choice"]], rng)
            last_seen[seat] = len(session["moves"])

        over = eng.is_over(state)
        scores = [round(s, 2) for s in eng.scores(state)]
        winners = list(eng.winners(state)) if over else []
        out = self.idea_dir / "playtest" / "table" / f"{label}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(session, indent=2), encoding="utf-8")

        decisions = len(session["moves"])
        arbitrary = sum(1 for m in session["moves"] if m["arbitrary"])
        record = {
            "label": label, "seats": seats, "seed": seed,
            "seed_blind": session["seed_blind"], "stuck": stuck,
            "finished": over, "decisions": decisions, "scores": scores,
            "winners": winners,
            "arbitrary_rate": round(arbitrary / max(decisions, 1), 3),
            "arbitrary_by_seat": {
                str(s): round(
                    sum(1 for m in session["moves"]
                        if m["seat"] == s and m["arbitrary"])
                    / max(sum(1 for m in session["moves"] if m["seat"] == s), 1),
                    3)
                for s in range(seats)},
            "session": str(out),
        }
        self.games.append(record)

        await self.collect_debriefs(seats, label, scores, winners, game_no,
                                    stuck, over)
        return record

    async def collect_debriefs(self, seats: int, label: str, scores: list,
                               winners: list, game_no: int, stuck: bool,
                               over: bool) -> None:
        """Scores and the winner go to every seat, and nothing else.

        A group playing the same game several times in an evening knows who
        won the last one, and the memory that builds on that is the only way
        the "did this game get smaller" question can be answered at all. What
        does not go out is any hidden state the game itself never reveals.
        """
        if stuck:
            ending = ("The game stopped: nobody had a legal move and the rules "
                      "do not say what happens then.")
        elif not over:
            ending = "The game hit the turn cap without reaching an ending."
        else:
            ending = f"Final scores {scores}. Winner(s): seat(s) {winners}."
        extra = ("" if game_no == 1 else
                 "\n\nThis was not your first game here, so add the two extra "
                 "lines the brief asks for from the second game on.")
        for seat in range(seats):
            reply = await self.ask_seat(
                seat, f"GAME OVER  {label}\n{ending}\n\nDebrief now, in six "
                      f"lines or fewer, following your brief.{extra}")
            self.debriefs.append({"game": label, "seat": seat,
                                  "text": reply.strip()})

    async def closing_question(self, seats_seen: set) -> None:
        for seat in sorted(seats_seen):
            reply = await self.ask_seat(
                seat, "The run is over. Answer the last question in your "
                      "brief: did this game get smaller?")
            self.debriefs.append({"game": "RUN END", "seat": seat,
                                  "text": reply.strip()})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_schedule(text: str) -> list:
    """`4:3,2:2` is three games at four seats then two games at two seats."""
    out = []
    for chunk in filter(None, (c.strip() for c in text.split(","))):
        seats, _, count = chunk.partition(":")
        out.append((int(seats), int(count or 1)))
    return out


async def run(args: argparse.Namespace) -> int:
    idea_dir = args.idea_dir.parent if args.idea_dir.is_file() else args.idea_dir
    idea_file = idea_dir / "idea.json"
    engine_path = args.engine or (idea_dir / "playtest" / "engine.py")
    if not engine_path.is_file():
        print(f"TABLE ERROR no engine at {engine_path}")
        return 2
    if not idea_file.is_file():
        print(f"TABLE ERROR no idea.json at {idea_file}")
        return 2

    eng = playtest.load_engine(engine_path)
    idea = json.loads(idea_file.read_text(encoding="utf-8"))
    schedule = parse_schedule(args.schedule)

    for seats, _ in schedule:
        problems = (playtest.validate_engine(eng)
                    or playtest.table_guard(eng, seats, args.seed))
        if problems:
            print("TABLE ERROR " + "; ".join(problems))
            return 2

    base_url = os.environ.get("PLAYTEST_BASE_URL", "").strip()
    api_key = os.environ.get("PLAYTEST_API_KEY", "").strip()
    model = args.model or os.environ.get("PLAYTEST_MODEL", "").strip()
    missing = [name for name, value in
               (("PLAYTEST_BASE_URL", base_url), ("PLAYTEST_API_KEY", api_key),
                ("PLAYTEST_MODEL", model)) if not value]
    if missing:
        print("TABLE ERROR set " + ", ".join(missing))
        return 2

    if args.driver == "sdk":
        os.environ.setdefault("ANTHROPIC_BASE_URL", base_url)
        os.environ.setdefault("ANTHROPIC_AUTH_TOKEN", api_key)
        backend: Backend = SdkBackend(model, args.max_tokens)
    else:
        backend = ChatBackend(base_url, api_key, model, args.wire,
                              args.max_tokens, not args.no_cache)

    brief = strip_frontmatter(PLAYER_BRIEF.read_text(encoding="utf-8"))
    rules = render_rules(idea)
    widest = max(seats for seats, _ in schedule)
    systems = {s: seat_system_prompt(brief, rules, s, widest,
                                     s == args.breaker_seat)
               for s in range(widest)}

    started = time.monotonic()
    run_state = Run(eng, idea_dir, backend, args.compact)
    seats_seen: set = set()
    game_no = 0
    try:
        for seats, count in schedule:
            for _ in range(count):
                game_no += 1
                label = f"{args.label_prefix}{game_no}"
                seed = args.seed + game_no * 13
                seats_seen |= set(range(seats))
                record = await run_state.play_game(seats, seed, label,
                                                   systems, game_no)
                print(f"  {label}  {seats}p seed {seed}  "
                      f"{record['decisions']} decisions  "
                      f"scores {record['scores']}  winners {record['winners']}"
                      f"  arbitrary {record['arbitrary_rate']:.0%}")
        await run_state.closing_question(seats_seen)
    finally:
        await backend.close()

    elapsed = time.monotonic() - started
    summary = {
        "slug": getattr(eng, "SLUG", idea_dir.name),
        "driver": backend.name, "model": model,
        "breaker_seat": args.breaker_seat,
        "seconds": round(elapsed, 1),
        "usage": run_state.usage,
        "leaks": run_state.leaked_seats(),
        "games": run_state.games,
        "rules_questions": run_state.questions,
        "debriefs": run_state.debriefs,
    }
    # The name carries the wire and the cache setting, not just the driver,
    # because the whole point of this tool right now is to run the same games
    # under several of them and compare, and a summary that overwrites its
    # predecessor makes that impossible.
    slug = re.sub(r"[^a-z0-9]+", "_", backend.name.lower()).strip("_")
    out = idea_dir / "playtest" / "table" / f"run_{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    use = run_state.usage
    total_in = use["in"] + use["cached"]
    print(f"\nTABLE RUN {backend.name}  {len(run_state.games)} games, "
          f"{sum(g['decisions'] for g in run_state.games)} decisions, "
          f"{elapsed:.0f}s")
    print(f"  tokens  in {total_in} (cached {use['cached']}), "
          f"out {use['out']}, calls {use['calls']}")
    print(f"  rules questions raised in play: {len(run_state.questions)}")
    leaks = run_state.leaked_seats()
    if leaks:
        print("  LEAK  a seat was sent something addressed to another seat: "
              + ", ".join(leaks))
    if any(g["seed_blind"] for g in run_state.games):
        print("  SEED BLIND  this engine deals the same opening every time, "
              "so games at one seat count are one game repeated")
    print(f"  summary {out}")
    return 0


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("idea_dir", type=Path)
    ap.add_argument("--schedule", default="4:3,2:2",
                    help="games per seat count, e.g. 4:3,2:2")
    ap.add_argument("--driver", choices=("chat", "sdk"), default="chat")
    ap.add_argument("--wire", choices=("anthropic", "openai"),
                    default="anthropic", help="chat driver only")
    ap.add_argument("--no-cache", action="store_true",
                    help="chat/anthropic only: drop the cache_control marker "
                         "on the static brief, to measure what it saves")
    ap.add_argument("--model", default="")
    ap.add_argument("--engine", type=Path, default=None)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--label-prefix", default="g")
    ap.add_argument("--breaker-seat", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--compact", action="store_true", default=True)
    ap.add_argument("--no-compact", dest="compact", action="store_false")
    return asyncio.run(run(ap.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
