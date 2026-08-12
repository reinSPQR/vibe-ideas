#!/usr/bin/env python3
"""generate_images.py — render each idea's "prompt" field in board-game/IDEAS.json
to a PNG via OpenRouter's Unified Image API, so a turn's 10 ideas can be
reviewed visually instead of only as text.

Mirrors the request/response contract already proven in this monorepo for
this exact model (panda-social-cc-agent's app/utils/jobs/concept_gen.py /
app/configs.py CONCEPT_IMAGE_*): OPENROUTER_API_KEY bearer auth, POST
https://openrouter.ai/api/v1/images, body {model, prompt, aspect_ratio,
resolution}, response data[0].b64_json (+ media_type).

Usage:
    OPENROUTER_API_KEY=sk-... python3 board-game/tools/generate_images.py --turn 5
    python3 board-game/tools/generate_images.py --turn 5 --ideas-file board-game/IDEAS.json

Best-effort by design: this is a human-review convenience, not part of the
sellability pipeline. A single idea's render failing is logged and skipped,
never fatal. Exit code is 0 whenever at least one image rendered (or there
were zero ideas to render); it's 2 only when nothing could be attempted at
all (missing API key) or every single idea failed, so a caller can tell
"partial/complete success" from "totally broken" without treating either as
a reason to stop the /goal loop.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import requests

OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"
DEFAULT_MODEL = "openai/gpt-image-2"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_RESOLUTION = "1K"
_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
_MAX_WORKERS = 3
_TIMEOUT_S = 180.0

# The CAD pipeline has no colour-assignment step: every build comes back in one
# uniform material regardless of what the prompt asks for. A colourful
# reference render would therefore differ from every build in a way we already
# know about and do not score, contaminating the vision-vs-build comparison at
# its source. So every render is pinned to the same unpainted single-material
# look the pipeline can actually deliver, and the ideator is told not to design
# around colour at all — distinction has to live in geometry.
MATERIAL_CLAUSE = (
    " Render as an unpainted single-material 3D print: one uniform matte "
    "off-white/light-grey filament throughout, no paint, no decals, no colour "
    "coding of any kind. All distinction between parts must read from shape, "
    "silhouette, height, engraved relief and surface texture alone. Neutral "
    "studio background, even lighting, no props."
)


@dataclass
class RenderResult:
    idea_id: int
    title: str
    ok: bool
    path: Path | None = None
    error: str | None = None


def _load_dotenv_fallback(repo_root: Path) -> None:
    """If OPENROUTER_API_KEY isn't already in the environment, look for a
    .env at the repo root and pull just that one key out of it. Not worth a
    python-dotenv dependency for a single variable."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "OPENROUTER_API_KEY":
            os.environ["OPENROUTER_API_KEY"] = value.strip().strip('"').strip("'")
            return


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "idea"


def _render_idea(
    idea: dict,
    *,
    api_key: str,
    model: str,
    aspect_ratio: str,
    resolution: str,
    out_dir: Path,
    field: str = "prompt",
) -> RenderResult:
    idea_id = idea.get("id")
    title = str(idea.get("title") or f"idea-{idea_id}")
    prompt = idea.get(field)
    if not prompt:
        return RenderResult(idea_id, title, ok=False, error=f"idea has no '{field}' field")

    body = {
        "model": model,
        "prompt": prompt + MATERIAL_CLAUSE,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://vibe.autonomous.ai",
        "X-Title": "board-game-ideator",
    }
    try:
        response = requests.post(
            OPENROUTER_IMAGES_URL, headers=headers, json=body, timeout=_TIMEOUT_S
        )
    except requests.RequestException as exc:
        return RenderResult(idea_id, title, ok=False, error=f"request failed: {exc}")

    if not response.ok:
        detail = response.text[:400]
        return RenderResult(
            idea_id, title, ok=False, error=f"HTTP {response.status_code}: {detail}"
        )

    try:
        data = response.json()
    except ValueError:
        return RenderResult(idea_id, title, ok=False, error="response was not valid JSON")

    items = data.get("data")
    first = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
    encoded = first.get("b64_json")
    if not isinstance(encoded, str) or not encoded:
        return RenderResult(
            idea_id, title, ok=False, error=f"no image in response: {json.dumps(data)[:300]}"
        )

    try:
        raw = base64.b64decode(encoded, validate=True)
    except ValueError:
        return RenderResult(idea_id, title, ok=False, error="invalid base64 image payload")

    media_type = str(first.get("media_type") or "image/png")
    extension = _EXTENSIONS.get(media_type, ".png")
    filename = f"idea-{idea_id:02d}-{_slugify(title)}{extension}"
    destination = out_dir / filename
    out_dir.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return RenderResult(idea_id, title, ok=True, path=destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turn", type=int, required=True, help="turn number, for the output path")
    parser.add_argument(
        "--ideas-file",
        default="board-game/IDEAS.json",
        help="path to the JSON file written by board-game-ideator (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="where to write PNGs (default: board-game/history/turn-<N>/images)",
    )
    parser.add_argument(
        "--latest-dir",
        default="board-game/images",
        help="convenience copy of this turn's images, cleared and repopulated each run (default: %(default)s)",
    )
    parser.add_argument(
        "--field",
        default="prompt",
        help=(
            "which field to render (default: %(default)s). Use --field cad_prompt "
            "--ideas-file board-game/CAD_PROMPTS.json for the back-translation "
            "pre-flight: rendering the cad_prompt ALONE, with no theme text and no "
            "sight of the vision render, shows what a reader who only has the prompt "
            "would build. If that image is missing a must_survive feature, the CAD "
            "pipeline will miss it too — caught in 20 seconds instead of 30 minutes."
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--aspect-ratio", default=DEFAULT_ASPECT_RATIO)
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    _load_dotenv_fallback(repo_root)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "OPENROUTER_API_KEY is not set (checked env and .env at repo root) — "
            "skipping image generation. Ideas are still complete without previews; "
            "set the key and re-run this script any time to backfill them.",
            file=sys.stderr,
        )
        return 2

    ideas_path = Path(args.ideas_file)
    try:
        payload = json.loads(ideas_path.read_text())
    except (OSError, ValueError) as exc:
        print(f"could not read/parse {ideas_path}: {exc}", file=sys.stderr)
        return 2

    ideas = payload.get("ideas") if isinstance(payload, dict) else None
    if not isinstance(ideas, list) or not ideas:
        print(f"no ideas found in {ideas_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else Path(f"board-game/history/turn-{args.turn}/images")

    results: list[RenderResult] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                _render_idea,
                idea,
                api_key=api_key,
                model=args.model,
                aspect_ratio=args.aspect_ratio,
                resolution=args.resolution,
                out_dir=out_dir,
                field=args.field,
            ): idea
            for idea in ideas
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda r: (r.idea_id is None, r.idea_id))
    succeeded = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    for r in succeeded:
        print(f"OK   idea {r.idea_id:>2} ({r.title}) -> {r.path}")
    for r in failed:
        print(f"FAIL idea {r.idea_id} ({r.title}): {r.error}", file=sys.stderr)

    latest_dir = Path(args.latest_dir)
    if succeeded:
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        latest_dir.mkdir(parents=True, exist_ok=True)
        for r in succeeded:
            shutil.copy2(r.path, latest_dir / r.path.name)

    print(f"IMAGES: {len(succeeded)}/{len(results)} generated (turn {args.turn})")
    if not succeeded:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
