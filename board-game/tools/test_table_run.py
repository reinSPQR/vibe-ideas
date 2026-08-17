"""test_table_run.py — fixtures for the played table, with no model.

`table_run.py` cannot be tested against a real endpoint on every change: it
would cost money, it would be slow, and worst of all its answers would move
between runs, so a failure would never tell you whether the harness broke or
the model had an off day. So the model is replaced by a local HTTP server that
answers deterministically, and everything that is actually this file's job
becomes checkable: that a seat only ever sees its own position, that a reply
is parsed strictly, that an unreadable reply stops the run instead of being
quietly played by a policy, that the session written replays through
`playtest.py`, and that the token accounting adds up.

The one thing these fixtures cannot check is whether the players say anything
worth reading. That needs a real model and it is what a real run is for.

    .venv/bin/python board-game/tools/test_table_run.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import playtest  # noqa: E402
import table_run  # noqa: E402

MOVE_LINE = re.compile(r"^  (\d+)  ", re.M)

# Fixed so the accounting is checkable by multiplication rather than by trust.
USAGE = {"input_tokens": 10, "output_tokens": 5,
         "cache_read_input_tokens": 7, "cache_creation_input_tokens": 0}

# A game small enough to finish in a handful of decisions, so a fixture run is
# a second rather than a minute, and simple enough that the expected scores can
# be worked out by hand: each seat takes tokens off a shared pile and the
# largest total wins.
ENGINE = '''
"""engine.py — fixture, an executable model of nothing in particular."""


class Undefined(Exception):
    """The rules do not say."""


SLUG = "fixture"
PLAYERS = (2, 4)
MAX_TURNS = 40
MOVE_KINDS = ("take",)
HIDDEN_INFO = False
ASSUMPTIONS = []
CHOICES = {}


def new_game(n_players, rng):
    pile = [1, 2, 3, 4, 5, 6, 7, 8]
    rng.shuffle(pile)
    return {"pile": pile, "held": [[] for _ in range(n_players)],
            "seat": 0, "n": n_players}


def player_to_move(state):
    return state["seat"]


def legal_moves(state):
    return [("take", i) for i in range(len(state["pile"]))]


def apply_move(state, move, rng):
    state["held"][state["seat"]].append(state["pile"].pop(move[1]))
    state["seat"] = (state["seat"] + 1) % state["n"]
    return state


def is_over(state):
    return not state["pile"]


def scores(state):
    return [float(sum(h)) for h in state["held"]]


def winners(state):
    best = max(scores(state))
    return [i for i, s in enumerate(scores(state)) if s == best]
'''

IDEA = {
    "slug": "fixture", "title": "Fixture", "concept": "Take tokens.",
    "players": {"min": 2, "max": 4}, "playtime_min": 5,
    "components": [{"name": "token", "qty": 8, "desc": "A token."}],
    "rules": {"setup": [{"text": "Shuffle the pile."}],
              "turn": [{"text": "Take one token."}],
              "win": {"text": "Most points wins."}},
}


def text_of(content) -> str:
    """A message body is a string on one wire and a list of blocks on another.

    The tool has to write both, so the stand-in endpoint has to read both,
    and the newlines have to survive: the fixture model finds its move by
    matching the numbered list in the position block, exactly as a real one
    would.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict))
    return str(content)


class Endpoint:
    """A model that always takes the first option, and can be told to misbehave."""

    def __init__(self, mode: str = "good"):
        self.mode = mode
        self.seen: list = []
        self.bodies: list = []
        self.server = HTTPServer(("127.0.0.1", 0), self._handler())
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _answer(self, text: str) -> str:
        self.seen.append(text)
        if "Debrief now" in text or "get smaller" in text:
            return "Nothing mattered.\nI would not play again."
        if self.mode == "unreadable":
            return "I think I will take the small one, it seems wise."
        if self.mode == "out_of_range":
            return "CHOICE 999\nWHY off the end\nARBITRARY no"
        idx = MOVE_LINE.search(text)
        return (f"CHOICE {idx.group(1) if idx else 0}\n"
                f"WHY first option\nARBITRARY yes")

    def _handler(self):
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def _json(self, reply: str) -> None:
                payload = {"content": [{"type": "text", "text": reply}],
                           "usage": USAGE}
                raw = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                size = int(self.headers["content-length"])
                body = json.loads(self.rfile.read(size))
                endpoint.bodies.append(body)
                self._json(endpoint._answer(
                    text_of(body["messages"][-1]["content"])))

        return Handler


def make_idea(root: Path) -> Path:
    idea_dir = root / "fixture"
    (idea_dir / "playtest").mkdir(parents=True)
    (idea_dir / "idea.json").write_text(json.dumps(IDEA), encoding="utf-8")
    (idea_dir / "playtest" / "engine.py").write_text(ENGINE, encoding="utf-8")
    return idea_dir


def run_table(idea_dir: Path, endpoint: Endpoint, extra: list) -> int:
    os.environ["PLAYTEST_BASE_URL"] = endpoint.url()
    os.environ["PLAYTEST_API_KEY"] = "fixture"
    os.environ["PLAYTEST_MODEL"] = "fixture-model"
    # The tool narrates a real run, which is right there and noise here.
    with contextlib.redirect_stdout(io.StringIO()):
        return table_run.main([str(idea_dir)] + extra)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def check_parse() -> list:
    """The strict half of the contract, checked without a server at all."""
    bad = []
    good = table_run.parse_reply(
        "CHOICE 2\nWHY holding back keeps both tiers open\nARBITRARY no\n"
        "RULES QUESTION rules:turn[5] says nothing about ties\n"
        "NOTE fourth turn running with nothing to weigh", 5)
    if not good:
        return ["a well-formed reply did not parse"]
    for field, want in (("choice", 2), ("arbitrary", False)):
        if good[field] != want:
            bad.append(f"{field} read as {good[field]!r}, wanted {want!r}")
    if good["question"] != ["rules:turn[5] says nothing about ties"]:
        bad.append(f"rules question read as {good['question']!r}")
    if good["note"] != ["fourth turn running with nothing to weigh"]:
        bad.append(f"note read as {good['note']!r}")
    if not table_run.parse_reply("CHOICE 1\nARBITRARY yes", 5)["arbitrary"]:
        bad.append("ARBITRARY yes was not read as arbitrary")

    # A reasoning model's scratch work turns up inside the reply on some
    # gateways. It has to be cut, not searched: a CHOICE the model wrote while
    # still weighing options is not the move it settled on.
    thought = table_run.parse_reply(
        "<mm:think>Maybe CHOICE 0, or CHOICE 1. Let me weigh both.</mm:think>\n"
        "CHOICE 4\nWHY it forces the reply I want\nARBITRARY no", 5)
    if not thought or thought["choice"] != 4:
        bad.append(f"a reply with a think block parsed as {thought!r}")
    tail = table_run.parse_reply(
        "still weighing this</think>\nCHOICE 2\nWHY settled\nARBITRARY no", 5)
    if not tail or tail["choice"] != 2:
        bad.append(f"a reply with a trimmed think block parsed as {tail!r}")
    if table_run.parse_reply(
            "<think>I could take CHOICE 1 here and then", 5) is not None:
        bad.append("read a move out of a thought the model never finished")

    for text, why in (
            ("I pick the second one", "prose with no CHOICE line"),
            ("CHOICE 9", "an index past the end of the list"),
            ("CHOICE two", "a spelled-out index"),
            ("the CHOICE 1 is inline", "CHOICE buried mid-line")):
        if table_run.parse_reply(text, 5) is not None:
            bad.append(f"accepted {why}")
    return bad


def check_full_run(idea_dir: Path) -> list:
    """A whole run: two seat counts, sessions on disk, accounting, no leak."""
    endpoint = Endpoint()
    bad = []
    try:
        code = run_table(idea_dir, endpoint,
                          ["--schedule", "4:1,2:1", "--label-prefix", "f"])
    finally:
        endpoint.stop()
    if code != 0:
        return [f"table_run exited {code}"]

    summary = json.loads(
        (idea_dir / "playtest" / "table"
         / "run_anthropic_cached.json").read_text(encoding="utf-8"))
    if len(summary["games"]) != 2:
        bad.append(f"{len(summary['games'])} games recorded, wanted 2")
    if summary["leaks"]:
        bad.append(f"leak reported on a run that routes by code: {summary['leaks']}")
    if summary["usage"]["calls"] < 8:
        bad.append(f"only {summary['usage']['calls']} calls billed")
    if summary["usage"]["cached"] != summary["usage"]["calls"] * 7:
        bad.append("cached tokens do not add up over the calls made")

    # Every seat gets a closing question, and every seat that played a game
    # gets a debrief for it, so a seat that sat out the 2p game still has to
    # be there at the end. That is the run keeping its players alive.
    ends = [d for d in summary["debriefs"] if d["game"] == "RUN END"]
    if len(ends) != 4:
        bad.append(f"{len(ends)} closing answers, wanted one per seat (4)")

    for record in summary["games"]:
        session = json.loads(Path(record["session"]).read_text(encoding="utf-8"))
        if any(m["by"] != "player" for m in session["moves"]):
            bad.append(f"{record['label']} has a move nobody played")
        eng = playtest.load_engine(Path(session["engine"]))
        state, _ = playtest.replay(eng, session)
        if not eng.is_over(state):
            bad.append(f"{record['label']} does not replay to a finished game")
        elif list(eng.winners(state)) != record["winners"]:
            bad.append(f"{record['label']} replays to different winners")
        if record["seed_blind"]:
            bad.append("a shuffling engine was called seed blind")
    return bad


def check_seat_isolation(idea_dir: Path) -> list:
    """No seat may ever be handed a block addressed to another seat."""
    endpoint = Endpoint()
    try:
        run_table(idea_dir, endpoint,
                   ["--schedule", "4:1", "--label-prefix", "iso"])
    finally:
        endpoint.stop()
    bad = []
    for text in endpoint.seen:
        addressed = set(re.findall(r"^YOU ARE seat (\d+)", text, re.M))
        if len(addressed) > 1:
            bad.append(f"one message addressed seats {sorted(addressed)}")
    return bad


def check_unreadable_stops(idea_dir: Path, mode: str) -> list:
    """A seat that cannot answer must stop the run, loudly.

    The tempting failure here is to let a scripted policy finish the game so
    the run produces something. It would produce a session file that reads
    exactly like a game players finished, which is the one outcome this whole
    stage exists to prevent.
    """
    endpoint = Endpoint(mode=mode)
    try:
        run_table(idea_dir, endpoint, ["--schedule", "2:1",
                                        "--label-prefix", f"{mode}_"])
    except SystemExit as exc:
        message = str(exc)
        if "TABLE ERROR" not in message:
            return [f"stopped with an unhelpful message: {message!r}"]
        return []
    finally:
        endpoint.stop()
    return [f"a {mode} reply did not stop the run"]


CASES = [
    ("reply_parsing_is_strict", lambda d: check_parse()),
    ("a_whole_run_end_to_end", check_full_run),
    ("no_seat_sees_another_seats_position", check_seat_isolation),
    ("prose_instead_of_a_choice_stops_the_run",
     lambda d: check_unreadable_stops(d, "unreadable")),
    ("an_index_past_the_end_stops_the_run",
     lambda d: check_unreadable_stops(d, "out_of_range")),
]


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, case in CASES:
            idea_dir = make_idea(Path(tmp) / name)
            try:
                bad = case(idea_dir)
            except Exception as exc:  # a crash is a failure, not a stack trace
                bad = [f"raised {type(exc).__name__}: {exc}"]
            if bad:
                failures += 1
                print(f"  FAIL  table_run/{name}")
                for line in bad:
                    print(f"          {line}")
            else:
                print(f"  ok  table_run/{name}")
    if failures:
        print(f"\n{failures} FAILED of {len(CASES)} cases")
        return 1
    print(f"\nALL PASS ({len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
