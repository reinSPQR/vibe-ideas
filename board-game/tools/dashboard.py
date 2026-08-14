#!/usr/bin/env python3
"""dashboard.py — a view of every idea in the queue, for the owner to skim
instead of scrolling Telegram history.

    python3 board-game/tools/dashboard.py                  # writes dashboard.html once
    python3 board-game/tools/dashboard.py --open            # and opens it
    python3 board-game/tools/dashboard.py --serve            # live, at localhost:8420
    python3 board-game/tools/dashboard.py --serve --open     # live, opened for you

Telegram stays the alert channel — the two gates that need a decision, plus
the journal narration as it happens. This is the other view of the same
data: every idea at once, current state first, so you can see where the
queue actually stands without reconstructing it from a chat scrollback.

`--serve` re-reads `QUEUE.json` and the journal log on every request (the
open tab also reloads itself every `--interval` seconds, 5 by default), so
the page never goes stale while the pipeline is running — still read-only,
nothing on the page writes back to the queue. It binds to 127.0.0.1 only:
this is pipeline internals, not something to expose on the network. Without
`--serve` it is the original one-shot file, for a quick look or for handing
someone a single HTML file.

This is the one place allowed to read `journal.JOURNAL_LOG` — see the warning
in `journal.py`'s docstring before adding a second one. Everything else here
(`QUEUE.json`, `idea.json`, `gate.json`, `review_*.md`, hero renders) was
already readable by any pipeline tool; this script only arranges it.

The page is self-contained (renders embedded as base64), so the one-shot file
opens straight from disk with no server, and `--serve` needs no separate
static assets either.
"""
from __future__ import annotations

import argparse
import base64
import html
import http.server
import json
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import journal  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
IDEAS = REPO_ROOT / "board-game" / "ideas"
QUEUE = REPO_ROOT / "board-game" / "QUEUE.json"
OUT = REPO_ROOT / "board-game" / "dashboard.html"

LENSES = ("printability", "fidelity", "playability")

# Rough front-to-back order: closest to shipping first, terminal states last —
# mirrors pipeline_queue.py's PRIORITY, plus the states it doesn't schedule.
STATE_ORDER = ["reviewed", "awaiting_ship", "built", "repairing", "approved",
               "awaiting_owner", "drafted", "briefed", "rules_ok", "proposed",
               "blocked", "shipped", "killed"]
STATE_COLOR = {
    "proposed": "#8a8f98", "rules_ok": "#6b7280", "briefed": "#6b7280",
    "drafted": "#2563eb", "awaiting_owner": "#d97706", "approved": "#2563eb",
    "built": "#2563eb", "repairing": "#dc2626", "reviewed": "#059669",
    "awaiting_ship": "#d97706", "shipped": "#059669", "killed": "#9ca3af",
    "blocked": "#dc2626",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def load_journal() -> dict[str, list[dict]]:
    """slug -> its entries from JOURNAL_LOG, oldest first. Missing file (no
    entry has been written since this feature shipped) is just an empty
    story per idea, not an error."""
    by_slug: dict[str, list[dict]] = {}
    if not journal.JOURNAL_LOG.is_file():
        return by_slug
    for line in journal.JOURNAL_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        by_slug.setdefault(rec.get("slug", ""), []).append(rec)
    return by_slug


def find_hero(slug: str) -> Path | None:
    home = IDEAS / slug
    for pattern in ("**/_assembled.png", "**/cover.png", "**/*_qa.png"):
        found = sorted(home.glob(pattern))
        if found:
            return found[0]
    return None


def embed_image(path: Path | None) -> str:
    if not path or not path.is_file():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def gate_summary(slug: str) -> dict:
    gate = read_json(IDEAS / slug / "project" / "gate.json")
    if not gate:
        return {}
    sliced = [v for v in (gate.get("slice") or {}).values() if v.get("print_min")]
    hours = sum(v["print_min"] for v in sliced) / 60.0 if sliced else None
    return {
        "pass": gate.get("pass"),
        "parts": gate.get("part_count"),
        "shapes": gate.get("distinct_shapes"),
        "hours": hours,
        "fails": gate.get("fails") or [],
    }


def lens_verdicts(slug: str) -> list[tuple[str, str]]:
    out = []
    for lens in LENSES:
        path = IDEAS / slug / f"review_{lens}.md"
        if not path.is_file():
            continue
        first = (path.read_text(encoding="utf-8").splitlines() or [""])[0]
        out.append((lens, first.replace("Verdict:", "").strip()))
    return out


def build_timeline(item: dict, entries: list[dict]) -> list[dict]:
    """Merge QUEUE.json's state transitions (always present, even predating
    this feature) with journal entries other than `kind == "state"` (which
    QUEUE.json's own log already covers) into one chronological story."""
    events = []
    for t in item.get("log") or []:
        note = t.get("note", "")
        summary = f"{t['from']} → {t['to']}" + (f"\n{note}" if note else "")
        events.append({"at": t["at"], "kind": "state", "by": "pipeline",
                        "summary": summary, "body": ""})
    for e in entries:
        if e.get("kind") == "state":
            continue
        events.append(e)
    events.sort(key=lambda e: e.get("at", ""))
    return events


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def render_timeline(events: list[dict]) -> str:
    if not events:
        return '<p class="muted">no entries yet</p>'
    rows = []
    for e in events:
        stamp = esc(e.get("at", ""))[:16].replace("T", " ")
        kind = esc(e.get("kind", "note"))
        by = esc(e.get("by", ""))
        summary = esc(e.get("summary", "")).replace("\n", "<br>")
        body = e.get("body", "")
        detail = (f'<details class="body"><summary>detail</summary>'
                  f'<pre>{esc(body)}</pre></details>') if body.strip() else ""
        rows.append(
            f'<li><span class="ts">{stamp}</span> '
            f'<span class="kind kind-{kind}">{kind}</span> '
            f'<span class="by">{by}</span>'
            f'<div class="summary">{summary}</div>{detail}</li>')
    return f'<ul class="timeline">{"".join(rows)}</ul>'


def render_idea(slug: str, item: dict, entries: list[dict]) -> str:
    idea = read_json(IDEAS / slug / "idea.json")
    state = item.get("state", "?")
    color = STATE_COLOR.get(state, "#6b7280")
    title = idea.get("title") or item.get("title") or slug
    concept = idea.get("concept", "")
    players = idea.get("players") or {}
    playtime = idea.get("playtime_min")
    repairs = item.get("repairs_used", 0)
    rework = item.get("rework_reason", "")

    hero = embed_image(find_hero(slug))
    hero_html = f'<img class="hero" src="{hero}" alt="{esc(title)}">' if hero else ""

    facts = []
    if players:
        facts.append(f"{esc(players.get('min', '?'))}–{esc(players.get('max', '?'))} players")
    if playtime:
        facts.append(f"~{esc(playtime)} min")
    facts_html = " · ".join(facts)

    gate = gate_summary(slug)
    gate_html = ""
    if gate:
        verdict = "PASS" if gate.get("pass") else "FAIL"
        vclass = "ok" if gate.get("pass") else "bad"
        hours = f" · ~{gate['hours']:.1f}h print" if gate.get("hours") else ""
        gate_html = (f'<div class="strip"><b class="{vclass}">GATE {verdict}</b> '
                     f'{esc(gate.get("parts"))} parts, {esc(gate.get("shapes"))} shapes'
                     f'{hours}</div>')
        if gate.get("fails"):
            items = "".join(f"<li>{esc(f)}</li>" for f in gate["fails"][:10])
            gate_html += f'<details class="body"><summary>{len(gate["fails"])} finding(s)</summary><ul>{items}</ul></details>'

    lenses = lens_verdicts(slug)
    lens_html = ""
    if lenses:
        items = " · ".join(f"{esc(name)}: {esc(v)}" for name, v in lenses)
        lens_html = f'<div class="strip">{items}</div>'

    rework_html = (f'<div class="strip warn">rework: {esc(rework)}</div>'
                   if rework else "")

    timeline = build_timeline(item, entries)

    return f"""
<section class="card" data-state="{esc(state)}">
  <div class="card-head">
    <h2>{esc(title)} <span class="slug">{esc(slug)}</span></h2>
    <span class="badge" style="background:{color}">{esc(state)}</span>
  </div>
  <div class="facts">{facts_html}{f' · repairs {repairs}/2' if repairs else ''}</div>
  {hero_html}
  <p class="concept">{esc(concept)}</p>
  {gate_html}
  {lens_html}
  {rework_html}
  <details class="timeline-toggle" open>
    <summary>timeline ({len(timeline)})</summary>
    {render_timeline(timeline)}
  </details>
</section>"""


def render(data: dict, journal_by_slug: dict, refresh_seconds: int | None = None) -> str:
    ideas = data.get("ideas") or {}

    def sort_key(kv):
        slug, item = kv
        state = item.get("state", "")
        try:
            rank = STATE_ORDER.index(state)
        except ValueError:
            rank = len(STATE_ORDER)
        return (rank, item.get("created", ""))

    ordered = sorted(ideas.items(), key=sort_key)

    counts: dict[str, int] = {}
    for _, item in ideas.items():
        counts[item.get("state", "?")] = counts.get(item.get("state", "?"), 0) + 1
    stats = " · ".join(f"{esc(k)}: {v}" for k, v in
                        sorted(counts.items(), key=lambda kv: -kv[1]))

    states_present = sorted({item.get("state", "?") for item in ideas.values()})
    filter_buttons = " ".join(
        f'<button class="filter" data-filter="{esc(s)}">{esc(s)}</button>'
        for s in states_present)

    cards = "".join(render_idea(slug, item, journal_by_slug.get(slug, []))
                     for slug, item in ordered)
    if not cards:
        cards = '<p class="muted">the queue is empty — nothing has been proposed yet.</p>'

    from datetime import datetime, timezone
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    live = f' · <span class="live">live, refreshing every {refresh_seconds}s</span>' \
        if refresh_seconds else ""
    refresh_script = (f"<script>setTimeout(function(){{location.reload();}}, "
                       f"{refresh_seconds * 1000});</script>") if refresh_seconds else ""

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>board-game pipeline</title>
<style>
  :root {{
    --bg:#f7f7f8; --card:#fff; --text:#1a1a1a; --muted:#6b7280;
    --border:#e5e7eb; --ok:#059669; --bad:#dc2626; --warn-bg:#fff7ed;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#15161a; --card:#1e2025; --text:#e5e7eb; --muted:#9ca3af;
             --border:#2c2f36; --ok:#34d399; --bad:#f87171; --warn-bg:#3a2a12; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font:14px/1.5 -apple-system,
          BlinkMacSystemFont,"Segoe UI",sans-serif; margin:0; padding:24px; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .meta {{ color:var(--muted); font-size:12px; margin-bottom:16px; }}
  .filters {{ margin-bottom:20px; }}
  .filter {{ background:var(--card); border:1px solid var(--border); color:var(--text);
             border-radius:6px; padding:4px 10px; margin:0 6px 6px 0; cursor:pointer;
             font-size:12px; }}
  .filter.active {{ background:var(--text); color:var(--bg); }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:10px;
           padding:16px 20px; margin-bottom:16px; max-width:760px; }}
  .card-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
  h2 {{ font-size:16px; margin:0; }}
  .slug {{ color:var(--muted); font-weight:400; font-size:12px; }}
  .badge {{ color:#fff; border-radius:999px; padding:3px 10px; font-size:12px;
            white-space:nowrap; }}
  .facts {{ color:var(--muted); font-size:12px; margin:4px 0 10px; }}
  .hero {{ max-width:100%; border-radius:8px; border:1px solid var(--border);
           margin-bottom:10px; display:block; }}
  .concept {{ margin:0 0 10px; }}
  .strip {{ font-size:12px; background:var(--bg); border-radius:6px; padding:6px 10px;
            margin-bottom:6px; }}
  .strip.warn {{ background:var(--warn-bg); }}
  .ok {{ color:var(--ok); }} .bad {{ color:var(--bad); }}
  details.body {{ font-size:12px; margin:4px 0 8px; }}
  details.body pre {{ white-space:pre-wrap; word-break:break-word; background:var(--bg);
                       padding:8px; border-radius:6px; max-height:300px; overflow:auto; }}
  .timeline-toggle > summary {{ cursor:pointer; font-size:12px; color:var(--muted); }}
  ul.timeline {{ list-style:none; margin:8px 0 0; padding:0; border-left:2px solid var(--border); }}
  ul.timeline li {{ padding:6px 0 6px 14px; margin-left:2px; border-bottom:1px dashed var(--border); }}
  ul.timeline li:last-child {{ border-bottom:none; }}
  .ts {{ color:var(--muted); font-size:11px; }}
  .kind {{ font-size:10px; text-transform:uppercase; letter-spacing:.04em;
           color:var(--muted); border:1px solid var(--border); border-radius:4px;
           padding:1px 5px; margin-left:6px; }}
  .by {{ font-size:11px; color:var(--muted); margin-left:6px; }}
  .summary {{ margin-top:3px; }}
  .muted {{ color:var(--muted); }}
  .live {{ color:var(--ok); }}
</style></head>
<body>
  <h1>board-game pipeline</h1>
  <div class="meta">generated {generated} · {len(ideas)} idea(s) · {stats}{live}</div>
  <div class="filters">
    <button class="filter active" data-filter="">all</button>
    {filter_buttons}
  </div>
  <div id="cards">{cards}</div>
<script>
  function applyFilter(f) {{
    document.querySelectorAll('.filter').forEach(function(b) {{
      b.classList.toggle('active', b.dataset.filter === f);
    }});
    document.querySelectorAll('.card').forEach(function(card) {{
      card.style.display = (!f || card.dataset.state === f) ? '' : 'none';
    }});
  }}
  document.querySelectorAll('.filter').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      sessionStorage.setItem('bgFilter', btn.dataset.filter);
      applyFilter(btn.dataset.filter);
    }});
  }});
  var saved = sessionStorage.getItem('bgFilter');
  if (saved) applyFilter(saved);
</script>
{refresh_script}
</body></html>"""


def make_handler(interval: int):
    """One handler class per server, closed over `interval` so the served page
    knows its own auto-refresh rate. Re-reads QUEUE.json and the journal log
    on every GET — this is a few small local files, not a scale concern, and
    reading fresh each time is the entire point of `--serve`."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in ("/", "/index.html"):
                self.send_response(404)
                self.end_headers()
                return
            data = read_json(QUEUE)
            journal_by_slug = load_journal()
            body = render(data, journal_by_slug, refresh_seconds=interval).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:  # noqa: A002
            pass  # an admin's own local tool doesn't need an access log

    return Handler


def cmd_serve(port: int, interval: int, do_open: bool) -> int:
    httpd = http.server.HTTPServer(("127.0.0.1", port), make_handler(interval))
    url = f"http://127.0.0.1:{port}/"
    refresh_note = f"refreshing every {interval}s" if interval else "no auto-refresh, reload manually"
    print(f"serving {url} ({refresh_note}) — Ctrl+C to stop")
    if do_open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--open", action="store_true", dest="do_open",
                     help="open the page in the default browser")
    ap.add_argument("--serve", action="store_true",
                     help="serve a live, auto-refreshing page instead of writing a static file")
    ap.add_argument("--port", type=int, default=8420, help="serve: port to listen on")
    ap.add_argument("--interval", type=int, default=0,
                     help="serve: seconds between auto-refresh of the open tab "
                          "(0 = no auto-refresh, reload manually)")
    args = ap.parse_args()

    if args.serve:
        return cmd_serve(args.port, args.interval, args.do_open)

    data = read_json(QUEUE)
    journal_by_slug = load_journal()
    OUT.write_text(render(data, journal_by_slug), encoding="utf-8")
    print(f"wrote {OUT}")
    if args.do_open:
        webbrowser.open(OUT.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
