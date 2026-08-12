#!/usr/bin/env python3
"""audit_turn.py — the mechanical half of the loop's integrity check.

A fidelity-first loop has more room to cheat than a score-first one, because
"the build matched the vision" is trivially winnable by shrinking the vision.
This script runs the checks that need no judgment; `board-game-auditor` does
the rest (ambition floor, condition falsifiability, answer provenance,
heuristic drift) and writes them up together.

Checks, and what each one catches:

  schema        `must_survive` is 5 ranked entries, each declaring at least
                one check — an entry that routes to no verifier is a mood,
                not a vision statement
  mix           exactly one `new`, one `twist`, one `reskin` idea
  coverage      every component and every must_survive feature is actually
                mentioned in the cad_prompt — catches a cad-writer quietly
                dropping the hard part so the build comes out clean
  freeze        first-shot artifacts still hash to what was captured, and
                were captured BEFORE the first repair job was submitted —
                catches repaired geometry being scored as first-shot
  ledger        one create job per idea, at most one edit — catches a silent
                resubmission of a failed build
  consistency   SCORES.json matches the evaluation_report.json numbers it
                claims to be reporting — the evaluator consumes measurements,
                it does not get to invent them
  tamper        no agent definition file changed during the turn
  budget        Learned Heuristics sections stay inside their word budget
  degeneracy    fidelity rising while ambition falls — the signature of a
                loop converging on featureless slabs

Exit code: 0 green, 1 amber (report and continue), 2 red (stop the loop).

Usage:
    python3 board-game/tools/audit_turn.py --turn 14
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RED, AMBER, GREEN = "RED", "AMBER", "GREEN"
_HEURISTIC_WORD_BUDGET = 1200
_STOPWORDS = {
    "the", "and", "with", "that", "this", "each", "from", "into", "onto", "must", "should",
    "have", "has", "are", "for", "not", "its", "their", "than", "then", "when", "which",
    "one", "two", "all", "any", "per", "plus", "over", "under", "same", "such", "very",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 3 and w not in _STOPWORDS}


class Findings:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.checked: list[str] = []

    def check(self, name: str) -> None:
        self.checked.append(name)

    def add(self, level: str, check: str, detail: str) -> None:
        self.rows.append((level, check, detail))

    @property
    def verdict(self) -> str:
        levels = {r[0] for r in self.rows}
        return RED if RED in levels else (AMBER if AMBER in levels else GREEN)


def audit_schema(ideas: list[dict], f: Findings) -> None:
    f.check("schema: must_survive shape")
    for idea in ideas:
        tag = f"idea {idea.get('id')} ({idea.get('title')})"
        ms = idea.get("must_survive") or []
        if len(ms) != 5:
            f.add(AMBER, "schema", f"{tag}: {len(ms)} must_survive entries, expected 5")
        ranks = [e.get("rank") for e in ms]
        if sorted(r for r in ranks if isinstance(r, int)) != list(range(1, len(ms) + 1)):
            f.add(AMBER, "schema", f"{tag}: ranks are {ranks}, expected a unique 1..{len(ms)}")
        for entry in ms:
            if not entry.get("geometric") and not entry.get("visual"):
                f.add(RED, "schema",
                      f"{tag} rank {entry.get('rank')}: declares no check at all — "
                      f"unverifiable conditions may not be scored")
        if not any(e.get("geometric") for e in ms):
            f.add(AMBER, "schema", f"{tag}: no entry has a geometric check — fidelity is entirely LLM-judged")


def audit_mix(ideas: list[dict], f: Findings) -> None:
    f.check("mix: one new / one twist / one reskin")
    paths = sorted((i.get("differentiation_path") or "?") for i in ideas)
    if paths != ["new", "reskin", "twist"]:
        f.add(AMBER, "mix", f"idea mix is {paths}, expected exactly new+twist+reskin")


def audit_coverage(ideas: list[dict], prompts: dict[int, str], f: Findings) -> None:
    f.check("coverage: cad_prompt covers components and must_survive")
    for idea in ideas:
        idea_id = idea.get("id")
        tag = f"idea {idea_id} ({idea.get('title')})"
        prompt_words = _words(prompts.get(idea_id, ""))
        if not prompt_words:
            f.add(RED, "coverage", f"{tag}: no cad_prompt found")
            continue
        for entry in idea.get("must_survive") or []:
            needed = _words(entry.get("feature", ""))
            if not needed:
                continue
            hit = len(needed & prompt_words) / len(needed)
            if hit < 0.5:
                f.add(AMBER, "coverage",
                      f"{tag} rank {entry.get('rank')}: only {hit:.0%} of the feature's terms appear in "
                      f"cad_prompt ('{entry.get('feature')}') — verify it was not quietly dropped")
        components = idea.get("components")
        comp_lines = components if isinstance(components, list) else str(components or "").split("\n")
        for line in comp_lines:
            needed = _words(str(line))
            if len(needed) < 3:
                continue
            if len(needed & prompt_words) / len(needed) < 0.4:
                f.add(AMBER, "coverage", f"{tag}: component line poorly represented in cad_prompt — {str(line)[:90]}")


def audit_freeze_and_ledger(builds: Path, f: Findings) -> None:
    f.check("freeze: first-shot artifacts untampered and pre-repair")
    f.check("ledger: one create, at most one edit per idea")
    f.check("provenance: concierge answers cite a spec field")
    for bdir in sorted(builds.glob("idea-*")):
        tag = bdir.name
        session_path = bdir / "session.json"
        if not session_path.exists():
            f.add(RED, "ledger", f"{tag}: no session.json — the build has no ledger at all")
            continue
        session = json.loads(session_path.read_text())

        jobs = session.get("jobs") or []
        creates = [j for j in jobs if j.get("type") == "create"]
        edits = [j for j in jobs if j.get("type") == "edit"]
        if len(creates) > 1:
            f.add(RED, "ledger",
                  f"{tag}: {len(creates)} create jobs — a failed build may have been silently resubmitted "
                  f"and the successful attempt reported as first-shot")
        if len(edits) > 1:
            f.add(AMBER, "ledger", f"{tag}: {len(edits)} edit jobs, expected at most 1 repair round")

        stage = (session.get("stages") or {}).get("first-shot")
        stage_dir = bdir / "first-shot"
        if stage and stage_dir.exists():
            manifest = stage_dir / "FREEZE.sha256"
            if not manifest.exists():
                f.add(RED, "freeze", f"{tag}: first-shot has no FREEZE.sha256")
            else:
                recorded = {}
                for line in manifest.read_text().splitlines():
                    if line.startswith("#") or "  " not in line:
                        continue
                    digest, rel = line.split("  ", 1)
                    recorded[rel] = digest
                drift = []
                for rel, digest in recorded.items():
                    path = stage_dir / rel
                    # evaluation_report.json + .eval/ are written after the freeze, by design
                    if rel.startswith(".eval/") or rel == "evaluation_report.json":
                        continue
                    if not path.exists():
                        drift.append(f"{rel} missing")
                    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                        drift.append(f"{rel} modified")
                if drift:
                    f.add(RED, "freeze", f"{tag}: first-shot artifacts changed after capture — {'; '.join(drift[:5])}")

            captured_at = stage.get("captured_at")
            first_edit = min((j.get("submitted_at") for j in edits if j.get("submitted_at")), default=None)
            if captured_at and first_edit and first_edit < captured_at:
                f.add(RED, "freeze",
                      f"{tag}: a repair job was submitted at {first_edit}, BEFORE first-shot was captured at "
                      f"{captured_at} — first-shot fidelity is contaminated by repaired geometry")

        answers = [e for e in (session.get("events") or []) if e.get("kind") == "answer"]
        unsourced = [e for e in answers if not e.get("source_field")]
        if unsourced:
            f.add(AMBER, "provenance",
                  f"{tag}: {len(unsourced)}/{len(answers)} clarifying answers cite no spec field — "
                  f"the pilot may have invented design decisions the ideator never made")


def audit_consistency(scores: dict, builds: Path, f: Findings) -> None:
    f.check("consistency: SCORES.json matches evaluation_report.json")
    for row in scores.get("ideas") or []:
        idea_id = row.get("id")
        matches = sorted(builds.glob(f"idea-{idea_id:02d}-*"))
        if not matches:
            continue
        report_path = matches[0] / "first-shot" / "evaluation_report.json"
        if not report_path.exists():
            if row.get("first_shot_status") == "done":
                f.add(RED, "consistency",
                      f"idea {idea_id}: scored as a completed build but has no first-shot evaluation_report.json")
            continue
        measured = json.loads(report_path.read_text()).get("geometric_fidelity")
        claimed = row.get("geometric_fidelity")
        if measured is None or claimed is None:
            continue
        if abs(float(measured) - float(claimed)) > 0.005:
            f.add(RED, "consistency",
                  f"idea {idea_id}: SCORES.json claims geometric_fidelity {claimed}, "
                  f"evaluation_report.json measured {measured}")


def audit_tamper(turn_dir: Path, agents_dir: Path, f: Findings) -> None:
    f.check("tamper: agent definitions unchanged during the turn")
    snapshot_path = turn_dir / "AGENT_HASHES.json"
    if not snapshot_path.exists():
        f.add(AMBER, "tamper", "no AGENT_HASHES.json snapshot for this turn — /goal should write one before evaluating")
        return
    snapshot = json.loads(snapshot_path.read_text())
    for name, expected in snapshot.items():
        path = agents_dir / name
        if not path.exists():
            f.add(RED, "tamper", f"{name} no longer exists")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            f.add(RED, "tamper",
                  f"{name} changed during the turn — only its own revise pass may edit it, "
                  f"and only after scoring")


def audit_budget(agents_dir: Path, f: Findings) -> None:
    f.check("budget: Learned Heuristics word counts")
    for name in ("board-game-ideator.md", "board-game-cad-writer.md"):
        path = agents_dir / name
        if not path.exists():
            continue
        text = path.read_text()
        marker = text.find("# Learned Heuristics")
        if marker < 0:
            continue
        words = len(text[marker:].split())
        if words > _HEURISTIC_WORD_BUDGET:
            f.add(AMBER, "budget",
                  f"{name}: Learned Heuristics is {words} words (budget {_HEURISTIC_WORD_BUDGET}) — "
                  f"consolidate rather than append; an unreadable heuristic set stops being applied")


def audit_degeneracy(history: Path, turn: int, live_scores: Path, f: Findings) -> None:
    f.check("degeneracy: fidelity up while ambition down")
    series = []
    for n in range(max(1, turn - 2), turn + 1):
        # The current turn is not archived until after this audit runs, so its
        # scores are still at the live top-level path.
        path = history / f"turn-{n}" / "SCORES.json"
        if n == turn and not path.exists():
            path = live_scores
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        ideas = data.get("ideas") or []
        if not ideas:
            continue
        fid = [i.get("geometric_fidelity") for i in ideas if i.get("geometric_fidelity") is not None]
        amb = [i.get("ambition_15") for i in ideas if i.get("ambition_15") is not None]
        if fid and amb:
            series.append((n, sum(fid) / len(fid), sum(amb) / len(amb)))
    if len(series) >= 2:
        (_, f0, a0), (_, f1, a1) = series[-2], series[-1]
        if f1 > f0 + 0.02 and a1 < a0 - 0.5:
            f.add(AMBER, "degeneracy",
                  f"fidelity rose {f0:.2f}->{f1:.2f} while ambition fell {a0:.1f}->{a1:.1f} — "
                  f"the loop may be buying fidelity by shrinking the vision")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--turn", type=int, required=True)
    parser.add_argument("--history-root", default="board-game/history")
    parser.add_argument("--ideas-file", default="board-game/IDEAS.json")
    parser.add_argument("--prompts-file", default="board-game/CAD_PROMPTS.json")
    parser.add_argument("--scores-file", default="board-game/SCORES.json")
    parser.add_argument("--agents-dir", default=".claude/agents")
    parser.add_argument("--out", default="board-game/INTEGRITY.md")
    args = parser.parse_args()

    history = Path(args.history_root)
    turn_dir = history / f"turn-{args.turn}"
    builds = turn_dir / "builds"
    f = Findings()

    try:
        ideas = json.loads(Path(args.ideas_file).read_text()).get("ideas") or []
    except (OSError, ValueError) as exc:
        print(f"cannot read {args.ideas_file}: {exc}", file=sys.stderr)
        return 2

    prompts: dict[int, str] = {}
    prompts_path = Path(args.prompts_file)
    if prompts_path.exists():
        for row in json.loads(prompts_path.read_text()).get("ideas") or []:
            prompts[row.get("id")] = row.get("cad_prompt") or ""
    else:
        f.add(RED, "coverage", f"{args.prompts_file} does not exist — the cad-writer produced nothing to audit")

    audit_schema(ideas, f)
    audit_mix(ideas, f)
    if prompts:
        audit_coverage(ideas, prompts, f)
    if builds.exists():
        audit_freeze_and_ledger(builds, f)
    else:
        f.add(RED, "ledger", f"{builds} does not exist — no builds were attempted this turn")

    scores_path = Path(args.scores_file)
    if scores_path.exists():
        audit_consistency(json.loads(scores_path.read_text()), builds, f)
    else:
        f.add(AMBER, "consistency", f"{args.scores_file} not written yet — run this after the evaluator")

    audit_tamper(turn_dir, Path(args.agents_dir), f)
    audit_budget(Path(args.agents_dir), f)
    audit_degeneracy(history, args.turn, scores_path, f)

    verdict = f.verdict
    lines = [f"\n### Turn {args.turn} — mechanical audit ({verdict})", "", f"_run at {_now()}_", ""]
    lines.append("Checked: " + ", ".join(f.checked))
    lines.append("")
    if f.rows:
        lines.append("| Level | Check | Detail |")
        lines.append("|-------|-------|--------|")
        for level, check, detail in f.rows:
            lines.append(f"| {level} | {check} | {detail.replace('|', '/')} |")
    else:
        lines.append("No findings.")
    lines.append("")

    out = Path(args.out)
    header = "" if out.exists() else "# INTEGRITY — loop self-monitoring\n"
    with out.open("a") as fh:
        fh.write(header + "\n".join(lines) + "\n")

    print(f"AUDIT: {verdict} ({len(f.rows)} findings, {len(f.checked)} checks) -> {out}")
    for level, check, detail in f.rows:
        print(f"  [{level}] {check}: {detail}")
    return {GREEN: 0, AMBER: 1, RED: 2}[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
