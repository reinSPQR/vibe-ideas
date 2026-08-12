#!/usr/bin/env python3
"""cad_session.py — drive ONE idea's CAD job through the real production
pipeline (panda-social-cc-agent's local-worker stack via its `tools/client`
API), one step at a time, so an agent can make the in-flight judgment calls
this pipeline actually asks for.

This replaces `generate_cad_builds.py`'s fire-and-wait model. That script
submitted a prompt, waited up to 40 minutes, and recorded a flat failure
whenever the job parked on a clarifying question — which is how 5 of 9
`cad_build_picks` across turns 11-13 scored zero while their most useful
diagnostic (the question text itself) was thrown away. Every park is a
decision point, and a script cannot make a decision; so this exposes each
step as a subcommand and lets `board-game-cad-pilot` drive.

Subcommands (all take --turn and --idea-id; state lives in session.json):

    submit    submit the cad_prompt as a `create` job (optionally with the
              production concept phase enabled)
    status    poll once; print status + any pending question / style
              directions the job is parked on
    wait      poll until the job reaches a terminal or parked state
    answer    resume a parked job with a free-text answer (awaiting_questions
              / awaiting_concept_input / awaiting_concept_selection feedback)
    select    resume a concept-selection park by picking a style set
    capture   download EVERYTHING for a finished build — review images plus
              the full CAD project (CadQuery source, .step, .stl parts) — and
              freeze it with a sha256 manifest
    edit      submit a repair round as an `edit` job against the same design

Every API call, park, answer and capture is appended to session.json. That
file is the job ledger `audit_turn.py` checks: it is what makes "the pilot
quietly resubmitted a failed build" and "repaired artifacts got reported as
first-shot" mechanically detectable rather than a matter of trust.

Usage:
    python3 board-game/tools/cad_session.py submit --turn 14 --idea-id 1 \\
        --title "Kiln Row" --prompt-file /tmp/idea-01.cad.txt --concept-phase
    python3 board-game/tools/cad_session.py wait   --turn 14 --idea-id 1
    python3 board-game/tools/cad_session.py answer --turn 14 --idea-id 1 \\
        --message "Tile thickness is 4mm; see components."
    python3 board-game/tools/cad_session.py capture --turn 14 --idea-id 1 \\
        --stage first-shot

Requires the local-worker Docker stack and `tools/client`'s API server
already running (see panda-social-cc-agent/docs/local-worker-setup.md). This
script never starts either.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CLIENT_URL = "http://localhost:4320"
LOCAL_GCS_HOST = "gcs"
_HTTP_TIMEOUT_S = 30.0
_POLL_INTERVAL_S = 15.0
_DEFAULT_WAIT_S = 45 * 60

# Terminal = the job is finished for good. Parked = it is waiting on us and
# will not advance until a message/selection arrives.
_TERMINAL = {"done", "failed", "canceled"}
_PARKED = {
    "awaiting_questions",
    "awaiting_plan_approval",
    "awaiting_concept_input",
    "awaiting_concept_selection",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "idea"


# --------------------------------------------------------------------------
# HTTP


def _http_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
        body = resp.read()
    return json.loads(body) if body else {}


def _http_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT_S) as resp:
        return resp.read()


def _proxy_url(client_url: str, artifact_url: str) -> str:
    """Local-worker mode publishes artifact urls on the `gcs` compose-service
    host, which does not resolve outside the compose network. The client's
    own artifact proxy dials the published port while preserving the Host
    header the fake-GCS server gates on. Real CDN urls pass through."""
    try:
        if urllib.parse.urlparse(artifact_url).hostname != LOCAL_GCS_HOST:
            return artifact_url
    except ValueError:
        return artifact_url
    quoted = urllib.parse.quote(artifact_url, safe="")
    return f"{client_url}/api/artifacts/proxy?url={quoted}"


# --------------------------------------------------------------------------
# Session ledger


def build_dir(turn: int, idea_id: int, title: str | None, root: Path) -> Path:
    """Resolve this idea's build directory. When --title is not supplied we
    glob for an existing `idea-NN-*` directory rather than guessing the slug,
    so every subcommand after `submit` can be called with just the id."""
    parent = root / f"turn-{turn}" / "builds"
    if title:
        return parent / f"idea-{idea_id:02d}-{_slugify(title)}"
    matches = sorted(parent.glob(f"idea-{idea_id:02d}-*"))
    if not matches:
        raise SystemExit(
            f"no build directory for idea {idea_id} under {parent} — run `submit` first "
            f"(or pass --title so the directory name can be derived)"
        )
    return matches[0]


def load_session(bdir: Path) -> dict:
    path = bdir / "session.json"
    if not path.exists():
        raise SystemExit(f"no session.json in {bdir} — run `submit` first")
    return json.loads(path.read_text())


def save_session(bdir: Path, session: dict) -> None:
    session["updated_at"] = _now()
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "session.json").write_text(json.dumps(session, indent=2, default=str))


def _log(session: dict, kind: str, **fields) -> None:
    session.setdefault("events", []).append({"at": _now(), "kind": kind, **fields})


def _active_job(session: dict) -> str:
    jobs = session.get("jobs") or []
    if not jobs:
        raise SystemExit("session has no submitted jobs yet")
    return jobs[-1]["job_id"]


# --------------------------------------------------------------------------
# Job view


def _job_view(client_url: str, job_id: str) -> dict:
    """The fields a pilot actually needs to decide what to do next, pulled out
    of the client's job document so the agent doesn't have to parse a large
    nested blob to find a single pending question."""
    job = _http_json("GET", f"{client_url}/api/jobs/{job_id}")
    spec = job.get("concept_spec") or {}
    directions = spec.get("style_directions") or []
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress"),
        "questions": job.get("questions"),
        "concept_pending_question": spec.get("pending_question"),
        "concept_selected_set_id": spec.get("selected_set_id"),
        "concept_style_directions": [
            {
                "set_id": d.get("set_id") or d.get("id"),
                "descriptor": d.get("descriptor") or d.get("name"),
                "images": d.get("images") or d.get("image_urls"),
            }
            for d in directions
            if isinstance(d, dict)
        ],
        "error": job.get("error"),
        "result": job.get("result"),
    }


# --------------------------------------------------------------------------
# Project download


def _walk_tree(nodes, prefix: str = "") -> list[str]:
    """Flatten `_tree.json` into relative file paths. Mirrors the monitor's
    web/src/artifacts.ts walker: the root array can carry a trailing
    {type:"report"} summary node, and an empty directory arrives with no
    `contents` key at all — both are no-ops rather than errors."""
    out: list[str] = []
    if not isinstance(nodes, list):
        return out
    for node in nodes:
        if not isinstance(node, dict):
            continue
        name = node.get("name")
        if node.get("type") == "file" and name:
            out.append(f"{prefix}{name}")
        elif node.get("type") == "directory" and name and isinstance(node.get("contents"), list):
            out.extend(_walk_tree(node["contents"], f"{prefix}{name}/"))
    return out


def download_project(client_url: str, project_url: str, dest: Path) -> tuple[int, list[str]]:
    """Download every file the design snapshot published — CadQuery source,
    .step, .stl parts, review images — not just the renders.

    Note `project_url` itself 404s if fetched directly: it is a bucket folder,
    so a path from `_tree.json` must be appended to it."""
    base = project_url.rstrip("/") + "/"
    tree = json.loads(_http_bytes(_proxy_url(client_url, base + "_tree.json")).decode())
    paths = _walk_tree(tree)
    errors: list[str] = []
    written = 0
    for rel in paths:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(_http_bytes(_proxy_url(client_url, base + rel)))
            written += 1
        except (urllib.error.URLError, OSError) as exc:
            errors.append(f"{rel}: {exc}")
    return written, errors


def freeze(stage_dir: Path) -> Path:
    """Write a sha256 manifest over everything captured for this stage.

    This is what makes first-shot artifacts tamper-evident. Vision Fidelity is
    scored on the FIRST build only; a repair round runs afterwards against the
    same design, so without a freeze there is nothing stopping repaired
    geometry from being scored as if it were first-shot — accidentally or
    otherwise. audit_turn.py recomputes these digests and cross-checks the
    freeze timestamp against the ledger's first edit-job submission."""
    lines = []
    for path in sorted(p for p in stage_dir.rglob("*") if p.is_file() and p.name != "FREEZE.sha256"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(stage_dir)}")
    manifest = stage_dir / "FREEZE.sha256"
    manifest.write_text(f"# frozen_at {_now()}\n" + "\n".join(lines) + "\n")
    return manifest


# --------------------------------------------------------------------------
# Subcommands


def cmd_submit(args) -> int:
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    bdir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.prompt_file).read_text().strip()
    if not prompt:
        print(f"{args.prompt_file} is empty", file=sys.stderr)
        return 2

    payload = {"type": "create", "prompt": prompt, "auto_build": not args.no_auto_build}
    if args.concept_phase:
        payload["concept_phase"] = True
    submission = _http_json("POST", f"{args.client_url}/api/jobs", payload)
    job_id = submission.get("job_id") or submission.get("id")
    if not job_id:
        print(f"no job_id in response: {submission}", file=sys.stderr)
        return 2

    session = {
        "turn": args.turn,
        "idea_id": args.idea_id,
        "title": args.title,
        "created_at": _now(),
        "jobs": [],
        "events": [],
        "questions_asked": 0,
    }
    if (bdir / "session.json").exists():
        session = load_session(bdir)
    session["jobs"].append(
        {
            "job_id": job_id,
            "type": "create",
            "design_id": submission.get("design_id"),
            "concept_phase": bool(args.concept_phase),
            "submitted_at": _now(),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        }
    )
    _log(session, "submit", job_id=job_id, job_type="create", concept_phase=bool(args.concept_phase))
    save_session(bdir, session)
    (bdir / "submitted_prompt.txt").write_text(prompt)
    print(json.dumps({"job_id": job_id, "design_id": submission.get("design_id"), "dir": str(bdir)}, indent=2))
    return 0


def cmd_status(args) -> int:
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    session = load_session(bdir)
    view = _job_view(args.client_url, args.job_id or _active_job(session))
    print(json.dumps(view, indent=2, default=str))
    return 0


def cmd_wait(args) -> int:
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    session = load_session(bdir)
    job_id = args.job_id or _active_job(session)
    deadline = time.monotonic() + args.timeout
    view = {}
    while time.monotonic() < deadline:
        view = _job_view(args.client_url, job_id)
        status = view.get("status")
        if status in _TERMINAL or status in _PARKED:
            if status in _PARKED:
                # A park is the pipeline telling us what the prompt failed to
                # specify. Count it: Build Reliability is penalised per
                # question, and CAD_QUESTIONS.md is built from these.
                session["questions_asked"] = session.get("questions_asked", 0) + 1
                _log(session, "parked", job_id=job_id, status=status,
                     questions=view.get("questions"),
                     concept_pending_question=view.get("concept_pending_question"))
            else:
                _log(session, "terminal", job_id=job_id, status=status)
            save_session(bdir, session)
            print(json.dumps(view, indent=2, default=str))
            return 0
        time.sleep(_POLL_INTERVAL_S)
    _log(session, "timeout", job_id=job_id, waited_s=args.timeout)
    save_session(bdir, session)
    print(json.dumps({**view, "status": "timeout"}, indent=2, default=str))
    return 1


def cmd_answer(args) -> int:
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    session = load_session(bdir)
    job_id = args.job_id or _active_job(session)
    before = _job_view(args.client_url, job_id)
    _http_json("POST", f"{args.client_url}/api/jobs/{job_id}/message", {"message": args.message})
    _log(
        session,
        "answer",
        job_id=job_id,
        parked_status=before.get("status"),
        question=before.get("questions") or before.get("concept_pending_question"),
        answer=args.message,
        # Provenance: which spec field the answer came from. The pilot may not
        # invent design decisions here — an unsourced answer is a spec gap to
        # report, not a call to make, and the auditor samples this field.
        source_field=args.source_field,
    )
    save_session(bdir, session)
    print(json.dumps({"ok": True, "job_id": job_id, "resumed_from": before.get("status")}, indent=2))
    return 0


def cmd_select(args) -> int:
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    session = load_session(bdir)
    job_id = args.job_id or _active_job(session)
    before = _job_view(args.client_url, job_id)
    _http_json("POST", f"{args.client_url}/api/jobs/{job_id}/message", {"set_id": args.set_id})
    _log(session, "select_concept", job_id=job_id, set_id=args.set_id,
         offered=before.get("concept_style_directions"), reason=args.reason)
    save_session(bdir, session)
    print(json.dumps({"ok": True, "job_id": job_id, "set_id": args.set_id}, indent=2))
    return 0


def cmd_capture(args) -> int:
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    session = load_session(bdir)
    job_id = args.job_id or _active_job(session)
    view = _job_view(args.client_url, job_id)
    if view.get("status") != "done":
        print(f"job {job_id} is {view.get('status')}, not done — nothing to capture", file=sys.stderr)
        return 2

    stage_dir = bdir / args.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    result = view.get("result") or {}
    notes: list[str] = []

    thumbnail_urls = result.get("thumbnail_urls") or []
    if thumbnail_urls:
        assembled_url = thumbnail_urls[0]
        try:
            (stage_dir / "assembled.png").write_bytes(_http_bytes(_proxy_url(args.client_url, assembled_url)))
        except (urllib.error.URLError, OSError) as exc:
            notes.append(f"assembled.png: {exc}")
        qa_url = assembled_url.rsplit("/", 1)[0] + "/_qa.png"
        try:
            (stage_dir / "qa.png").write_bytes(_http_bytes(_proxy_url(args.client_url, qa_url)))
        except (urllib.error.URLError, OSError) as exc:
            notes.append(f"qa.png: {exc}")
    else:
        notes.append("job done but result carried no thumbnail_urls")

    project_url = result.get("project_url")
    files_written = 0
    if project_url:
        files_written, errors = download_project(args.client_url, project_url, stage_dir / "project")
        notes.extend(errors[:10])
    else:
        notes.append("job done but result carried no project_url — no CAD source/STEP/STL captured")

    (stage_dir / "job_result.json").write_text(json.dumps(view, indent=2, default=str))
    freeze_path = freeze(stage_dir)

    session.setdefault("stages", {})[args.stage] = {
        "captured_at": _now(),
        "job_id": job_id,
        "project_files": files_written,
        "review_fix": (result.get("review_fix") or {}),
        "notes": notes,
        "freeze": str(freeze_path.relative_to(bdir)),
    }
    _log(session, "capture", job_id=job_id, stage=args.stage, project_files=files_written, notes=notes)
    save_session(bdir, session)
    print(json.dumps({"stage": args.stage, "project_files": files_written, "notes": notes,
                      "dir": str(stage_dir)}, indent=2))
    return 0


def cmd_edit(args) -> int:
    """Submit a repair round against the design the create job produced.

    `edit` needs the design's latest history id; GET /api/designs/:id resolves
    it, which is the same resolution the monitor UI does."""
    bdir = build_dir(args.turn, args.idea_id, args.title, Path(args.history_root))
    session = load_session(bdir)
    if not (session.get("stages") or {}).get("first-shot"):
        print("refusing to submit a repair round before first-shot has been captured and frozen "
              "— first-shot fidelity is what gets scored, and it must be recorded first",
              file=sys.stderr)
        return 2

    create_job = next((j for j in session["jobs"] if j["type"] == "create"), None)
    design_id = (create_job or {}).get("design_id")
    if not design_id:
        view = _job_view(args.client_url, (create_job or {}).get("job_id") or _active_job(session))
        design_id = (view.get("result") or {}).get("design_id")
    if not design_id:
        print("could not resolve design_id for this idea", file=sys.stderr)
        return 2

    design = _http_json("GET", f"{args.client_url}/api/designs/{design_id}")
    history_id = design.get("latest_history_id")
    if not history_id:
        print(f"design {design_id} has no latest_history_id — nothing to edit against", file=sys.stderr)
        return 2

    prompt = Path(args.prompt_file).read_text().strip()
    submission = _http_json(
        "POST",
        f"{args.client_url}/api/jobs",
        {
            "type": "edit",
            "prompt": prompt,
            "auto_build": True,
            "target_design_id": design_id,
            "source_history_id": history_id,
        },
    )
    job_id = submission.get("job_id") or submission.get("id")
    if not job_id:
        print(f"no job_id in response: {submission}", file=sys.stderr)
        return 2

    session["jobs"].append({
        "job_id": job_id,
        "type": "edit",
        "design_id": design_id,
        "source_history_id": history_id,
        "submitted_at": _now(),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    })
    _log(session, "submit", job_id=job_id, job_type="edit", design_id=design_id)
    save_session(bdir, session)
    (bdir / "repair_prompt.txt").write_text(prompt)
    print(json.dumps({"job_id": job_id, "design_id": design_id, "source_history_id": history_id}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client-url", default=DEFAULT_CLIENT_URL)
    parser.add_argument("--history-root", default="board-game/history")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, *, title_required=False):
        p.add_argument("--turn", type=int, required=True)
        p.add_argument("--idea-id", type=int, required=True)
        p.add_argument("--title", default=None, required=title_required,
                       help="only needed on submit; later commands find the directory by id")
        p.add_argument("--job-id", default=None, help="defaults to the most recent job in session.json")

    p = sub.add_parser("submit"); common(p, title_required=True)
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--concept-phase", action="store_true",
                   help="run the production concept phase (Q&A + 3 style-direction sets) before CAD")
    p.add_argument("--no-auto-build", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("status"); common(p); p.set_defaults(func=cmd_status)

    p = sub.add_parser("wait"); common(p)
    p.add_argument("--timeout", type=int, default=_DEFAULT_WAIT_S)
    p.set_defaults(func=cmd_wait)

    p = sub.add_parser("answer"); common(p)
    p.add_argument("--message", required=True)
    p.add_argument("--source-field", default=None,
                   help="which spec field this answer was derived from (components, art_direction, ...)")
    p.set_defaults(func=cmd_answer)

    p = sub.add_parser("select"); common(p)
    p.add_argument("--set-id", required=True)
    p.add_argument("--reason", default=None)
    p.set_defaults(func=cmd_select)

    p = sub.add_parser("capture"); common(p)
    p.add_argument("--stage", choices=["first-shot", "repaired"], required=True)
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("edit"); common(p)
    p.add_argument("--prompt-file", required=True)
    p.set_defaults(func=cmd_edit)

    args = parser.parse_args()
    try:
        return args.func(args)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        print(f"HTTP {exc.code} from client API: {detail}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"client API unreachable at {args.client_url}: {exc}\n"
              f"the local-worker Docker stack and tools/client API server must already be running",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
