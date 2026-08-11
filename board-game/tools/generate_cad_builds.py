#!/usr/bin/env python3
"""generate_cad_builds.py — run this turn's `cad_build_picks` (up to 3 ideas)
through the real production CAD-generation pipeline (panda-social-cc-agent's
local-worker Docker stack, via its `tools/client` API), so a bounded subset
of a turn's ideas can be reviewed as actual built objects, not just text.

For each picked idea: submits its `cad_prompt` as a real `create` job
(`POST {client-url}/api/jobs`), polls to a terminal status, downloads the
plain CAD review render (`_assembled.png`) and the 8-view QA sheet
(`_qa.png`) via the client's local-GCS artifact proxy, then converts the
review render into a photoreal product photo by shelling out to the real
production code that does this in the shipped app —
`python -m app.utils.thumbnails.ai_thumbnail` — inside the already-built
worker container (no reimplementation, no new dependency install).

Usage:
    python3 board-game/tools/generate_cad_builds.py --turn 10
    python3 board-game/tools/generate_cad_builds.py --turn 10 \\
        --ideas-file board-game/IDEAS.json \\
        --panda-repo /path/to/panda-social-cc-agent

Requires the local-worker Docker stack AND `tools/client`'s API server
already running (this script never starts them — see
panda-social-cc-agent/docs/local-worker-setup.md). If the client API isn't
reachable, or `OPENROUTER_API_KEY` isn't set inside the worker container,
this is logged and the run degrades gracefully rather than crashing.

Best-effort by design, same contract as generate_images.py: a single idea's
build failing (or parking on a clarifying question this script won't guess
an answer to) is logged and skipped, never fatal to the others. Exit code
is 0 whenever at least one idea's build completed; 2 only when nothing
could be attempted at all (client unreachable, no picks) or every pick
failed/parked, so a caller (the /goal loop) can treat either "partial
success" or "totally unreachable" as informational rather than a reason to
stop.

Every picked idea gets an `out_dir`/`manifest.json` written, regardless of
outcome — a park/timeout/failure is no longer diagnostically silent. The
manifest's `status` field always reflects the real outcome
(`done`/`awaiting_questions`/`timeout`/`failed`/`submit_error`/etc.), and
non-`done` manifests additionally carry `error` (a short human-readable
reason where available) and `raw_job` (the full job-status response the
API returned, when one was received) so a downstream reader can see
*why* a pick didn't complete instead of inferring it from a missing
directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CLIENT_URL = "http://localhost:4320"
LOCAL_GCS_HOST = "gcs"
_MAX_WORKERS = 3
_POLL_INTERVAL_S = 15.0
_JOB_TIMEOUT_S = 40 * 60
_HTTP_TIMEOUT_S = 20.0
_TERMINAL = {"done", "failed", "canceled"}
_WORKER_SERVICE = "worker"


@dataclass
class BuildResult:
    idea_id: int
    title: str
    ok: bool
    outcome: str  # "done" | "failed" | "canceled" | "parked_awaiting_questions" | "timeout" | "submit_error"
    out_dir: Path | None = None
    job_id: str | None = None
    design_id: str | None = None
    review_fix: dict | None = None
    wall_time_s: float | None = None
    error: str | None = None


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "idea"


def _http_json(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def _http_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT_S) as resp:
        return resp.read()


def _client_reachable(client_url: str) -> bool:
    try:
        req = urllib.request.Request(f"{client_url}/api/jobs/000000000000000000000000")
        urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S)
        return True
    except urllib.error.HTTPError as exc:
        # 400/404 still means the server answered — that's "reachable".
        return exc.code < 500
    except (urllib.error.URLError, OSError):
        return False


def _proxy_url(client_url: str, artifact_url: str) -> str:
    from urllib.parse import quote

    return f"{client_url}/api/artifacts/proxy?url={quote(artifact_url, safe='')}"


def _submit_job(client_url: str, prompt: str) -> dict:
    return _http_json(
        "POST",
        f"{client_url}/api/jobs",
        {"type": "create", "prompt": prompt, "auto_build": True},
    )


def _poll_job(client_url: str, job_id: str) -> dict:
    deadline = time.monotonic() + _JOB_TIMEOUT_S
    while time.monotonic() < deadline:
        job = _http_json("GET", f"{client_url}/api/jobs/{job_id}")
        status = job.get("status")
        if status in _TERMINAL or status == "awaiting_questions":
            return job
        time.sleep(_POLL_INTERVAL_S)
    return {"status": "timeout"}


_WORKER_INDEX = 1  # pin every docker-compose call in one conversion to the
                    # same replica — cp/exec on a bare (unindexed) service
                    # name can each resolve to a *different* replica when the
                    # service is scaled, so the generation step and the
                    # output copy silently land on different containers.


def _run_ai_thumbnail(
    compose_file: Path, local_png: Path, job_id: str, out_dir: Path
) -> tuple[Path | None, str | None]:
    """Convert a plain CAD review render into a photoreal product photo by
    shelling out to the real production code (app.utils.thumbnails.ai_thumbnail)
    inside the already-built worker container. Returns (local_path, None) on
    success, (None, error_string) on failure. All docker-compose calls are
    pinned to the same replica (see _WORKER_INDEX) and the output filename's
    extension is discovered rather than assumed — ai_thumbnail corrects it to
    match whatever format the model actually returns (e.g. Seedream returns
    JPEG even when a .png output path is requested)."""
    remote_in = f"/tmp/cadbuild-{job_id}.png"
    remote_out_base = f"/tmp/cadbuild-{job_id}-photo"

    def _run(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True, timeout=180)

    def _compose(*args: str) -> list[str]:
        return ["docker", "compose", "-f", str(compose_file), *args]

    cp_in = _run(_compose("cp", "--index", str(_WORKER_INDEX), str(local_png), f"{_WORKER_SERVICE}:{remote_in}"))
    if cp_in.returncode != 0:
        return None, f"docker cp (in) failed: {cp_in.stderr[:300]}"

    gen = _run(
        _compose(
            "exec", "-T", "--index", str(_WORKER_INDEX), _WORKER_SERVICE,
            "python", "-m", "app.utils.thumbnails.ai_thumbnail",
            "--image", remote_in, "--out", f"{remote_out_base}.png",
        )
    )
    if gen.returncode != 0:
        return None, f"ai_thumbnail generation failed: {(gen.stderr or gen.stdout)[:300]}"

    find = _run(
        _compose(
            "exec", "-T", "--index", str(_WORKER_INDEX), _WORKER_SERVICE,
            "sh", "-c", f"ls {remote_out_base}.* 2>/dev/null | head -1",
        )
    )
    remote_actual = find.stdout.strip()
    if find.returncode != 0 or not remote_actual:
        return None, f"generated photo not found under {remote_out_base}.*: {(find.stderr or gen.stdout)[:300]}"

    out_dir.mkdir(parents=True, exist_ok=True)
    local_ext = Path(remote_actual).suffix or ".png"
    dest = out_dir / f"photo{local_ext}"
    cp_out = _run(_compose("cp", "--index", str(_WORKER_INDEX), f"{_WORKER_SERVICE}:{remote_actual}", str(dest)))
    if cp_out.returncode != 0:
        return None, f"docker cp (out) failed: {cp_out.stderr[:300]}"
    return dest, None


def _build_idea(
    idea: dict,
    *,
    client_url: str,
    compose_file: Path,
    out_root: Path,
) -> BuildResult:
    idea_id = idea.get("id")
    title = str(idea.get("title") or f"idea-{idea_id}")
    out_dir = out_root / f"idea-{idea_id:02d}-{_slugify(title)}"
    prompt = idea.get("cad_prompt")

    def _write_manifest(
        *, status: str, job_id: str | None = None, design_id: str | None = None,
        wall_time_s: float | None = None, error: str | None = None,
        raw_job: dict | None = None, review_fix: dict | None = None,
        photo_file: str | None = None, photo_error: str | None = None,
    ) -> None:
        # Always write a manifest, even on park/timeout/failure — this is the
        # only diagnostic artifact a non-done pick leaves behind, so it
        # carries whatever the job API actually returned (raw_job) rather
        # than forcing downstream readers to infer "missing dir == parked".
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "idea_id": idea_id,
            "title": title,
            "job_id": job_id,
            "design_id": design_id,
            "status": status,
            "review_fix": review_fix,
            "wall_time_s": round(wall_time_s, 1) if wall_time_s is not None else None,
            "photo_file": photo_file,
            "photo_error": photo_error,
            "error": error,
            "raw_job": raw_job,
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    if not prompt:
        _write_manifest(status="submit_error", error="idea has no 'cad_prompt' field")
        return BuildResult(idea_id, title, ok=False, outcome="submit_error", out_dir=out_dir, error="idea has no 'cad_prompt' field")

    start = time.monotonic()
    try:
        submission = _submit_job(client_url, prompt)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _write_manifest(status="submit_error", error=f"submit failed: {exc}", wall_time_s=time.monotonic() - start)
        return BuildResult(idea_id, title, ok=False, outcome="submit_error", out_dir=out_dir, error=f"submit failed: {exc}")

    job_id = submission.get("job_id")
    design_id = submission.get("target_design_id")
    if not job_id:
        _write_manifest(status="submit_error", error=f"no job_id in response: {submission}", raw_job=submission, wall_time_s=time.monotonic() - start)
        return BuildResult(idea_id, title, ok=False, outcome="submit_error", out_dir=out_dir, error=f"no job_id in response: {submission}")

    try:
        job = _poll_job(client_url, job_id)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _write_manifest(status="submit_error", job_id=job_id, design_id=design_id, error=f"poll failed: {exc}", wall_time_s=time.monotonic() - start)
        return BuildResult(idea_id, title, ok=False, outcome="submit_error", out_dir=out_dir, job_id=job_id, design_id=design_id, error=f"poll failed: {exc}")

    wall_time_s = time.monotonic() - start
    status = job.get("status")

    if status == "awaiting_questions":
        _write_manifest(status="awaiting_questions", job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, raw_job=job)
        return BuildResult(idea_id, title, ok=False, outcome="parked_awaiting_questions", out_dir=out_dir, job_id=job_id, design_id=design_id, wall_time_s=wall_time_s)
    if status == "timeout":
        _write_manifest(status="timeout", job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, raw_job=job)
        return BuildResult(idea_id, title, ok=False, outcome="timeout", out_dir=out_dir, job_id=job_id, design_id=design_id, wall_time_s=wall_time_s)
    if status != "done":
        _write_manifest(status=status or "failed", job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, error=str(job.get("error")), raw_job=job)
        return BuildResult(idea_id, title, ok=False, outcome=status or "failed", out_dir=out_dir, job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, error=str(job.get("error")))

    result = job.get("result") or {}
    thumbnail_urls = result.get("thumbnail_urls") or []
    if not thumbnail_urls:
        _write_manifest(status="done", job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, error="job done but no thumbnail_urls in result", raw_job=job)
        return BuildResult(idea_id, title, ok=False, outcome="done", out_dir=out_dir, job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, error="job done but no thumbnail_urls in result")

    assembled_url = thumbnail_urls[0]
    qa_url = assembled_url.rsplit("/", 1)[0] + "/_qa.png"

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        (out_dir / "assembled.png").write_bytes(_http_bytes(_proxy_url(client_url, assembled_url)))
    except (urllib.error.URLError, OSError) as exc:
        _write_manifest(status="done", job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, error=f"could not fetch assembled.png: {exc}", raw_job=job)
        return BuildResult(idea_id, title, ok=False, outcome="done", out_dir=out_dir, job_id=job_id, design_id=design_id, wall_time_s=wall_time_s, error=f"could not fetch assembled.png: {exc}")
    try:
        (out_dir / "qa.png").write_bytes(_http_bytes(_proxy_url(client_url, qa_url)))
    except (urllib.error.URLError, OSError):
        pass  # qa.png is supporting evidence only, non-fatal if missing

    photo_path, photo_error = _run_ai_thumbnail(compose_file, out_dir / "assembled.png", job_id, out_dir)

    _write_manifest(
        status="done", job_id=job_id, design_id=design_id, wall_time_s=wall_time_s,
        review_fix=result.get("review_fix"),
        photo_file=photo_path.name if photo_path else None,
        photo_error=photo_error,
    )

    return BuildResult(
        idea_id, title, ok=True, outcome="done", out_dir=out_dir, job_id=job_id,
        design_id=design_id, review_fix=result.get("review_fix"), wall_time_s=wall_time_s,
        error=f"photo generation failed: {photo_error}" if photo_error else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--turn", type=int, required=True, help="turn number, for the output path")
    parser.add_argument("--ideas-file", default="board-game/IDEAS.json", help="path to the JSON file written by board-game-ideator (default: %(default)s)")
    parser.add_argument("--client-url", default=DEFAULT_CLIENT_URL, help="panda-social-cc-agent tools/client API base URL (default: %(default)s)")
    parser.add_argument("--panda-repo", default=None, help="path to panda-social-cc-agent repo root (default: sibling directory, or $PANDA_AGENT_REPO)")
    parser.add_argument("--out-dir", default=None, help="where to write per-idea build artifacts (default: board-game/history/turn-<N>/cad-builds)")
    args = parser.parse_args()

    if not _client_reachable(args.client_url):
        print(
            f"local CAD test infra not reachable at {args.client_url} "
            "(is docker-compose.local-worker.yml + tools/client running? "
            "see panda-social-cc-agent/docs/local-worker-setup.md) — "
            "skipping CAD reality check this turn.",
            file=sys.stderr,
        )
        return 2

    repo_root = Path(__file__).resolve().parents[2]
    panda_repo = Path(args.panda_repo) if args.panda_repo else Path(
        os.environ.get("PANDA_AGENT_REPO", str(repo_root.parent / "panda-social-cc-agent"))
    )
    compose_file = panda_repo / "docker-compose.local-worker.yml"
    if not compose_file.exists():
        print(f"docker-compose.local-worker.yml not found at {compose_file} — skipping CAD reality check this turn.", file=sys.stderr)
        return 2

    ideas_path = Path(args.ideas_file)
    try:
        payload = json.loads(ideas_path.read_text())
    except (OSError, ValueError) as exc:
        print(f"could not read/parse {ideas_path}: {exc}", file=sys.stderr)
        return 2

    ideas = payload.get("ideas") if isinstance(payload, dict) else None
    picks = payload.get("cad_build_picks") if isinstance(payload, dict) else None
    if not isinstance(ideas, list) or not ideas or not isinstance(picks, list) or not picks:
        print(f"no ideas / cad_build_picks found in {ideas_path}", file=sys.stderr)
        return 2

    by_id = {idea.get("id"): idea for idea in ideas}
    picked_ideas = []
    for pick in picks:
        pick_id = pick.get("id") if isinstance(pick, dict) else None
        idea = by_id.get(pick_id)
        if idea is None:
            print(f"cad_build_picks references unknown id {pick_id!r} — skipping", file=sys.stderr)
            continue
        picked_ideas.append(idea)

    if not picked_ideas:
        print("no valid cad_build_picks resolved to ideas", file=sys.stderr)
        return 2

    out_root = Path(args.out_dir) if args.out_dir else Path(f"board-game/history/turn-{args.turn}/cad-builds")
    out_root.mkdir(parents=True, exist_ok=True)

    results: list[BuildResult] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                _build_idea,
                idea,
                client_url=args.client_url,
                compose_file=compose_file,
                out_root=out_root,
            ): idea
            for idea in picked_ideas
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda r: (r.idea_id is None, r.idea_id))
    succeeded = [r for r in results if r.ok]
    parked = [r for r in results if r.outcome == "parked_awaiting_questions"]
    failed = [r for r in results if not r.ok and r.outcome != "parked_awaiting_questions"]

    for r in succeeded:
        note = f" (photo generation issue: {r.error})" if r.error else ""
        print(f"OK   idea {r.idea_id:>2} ({r.title}) -> {r.out_dir}{note}")
    for r in parked:
        print(f"PARK idea {r.idea_id} ({r.title}): job {r.job_id} parked awaiting_questions — needs a human answer, skipped", file=sys.stderr)
    for r in failed:
        print(f"FAIL idea {r.idea_id} ({r.title}) [{r.outcome}]: {r.error}", file=sys.stderr)

    print(f"CAD_BUILDS: {len(succeeded)}/{len(picked_ideas)} done, {len(parked)} parked, {len(failed)} failed (turn {args.turn})")
    if not succeeded:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
