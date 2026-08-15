#!/usr/bin/env python3
"""graduation_check.py — every lesson that claims to have become code, checked
against the code.

    .venv/bin/python board-game/tools/graduation_check.py

`lessons.md`'s rule is that a lesson which has cost two builds stops being
prose and becomes a lint rule, a threshold, a block, or a constraint in an
agent's template, and is then marked `[GRADUATED -> ...]`. That marker is a
claim, and until now nothing has ever checked it.

An unchecked claim rots two ways that look identical from outside: a refactor
deletes the rule and leaves the marker behind, or the marker was optimistic the
day it was written. Both end the same place — lessons.md says the pipeline is
protected against something it is not, and the lesson is not in the build
prompts either, because graduating it is exactly what took it out of them. A
graduated lesson that was never landed is worse than one that never graduated.

This is also what makes `improve.py` safe to run unattended. That session can
edit `gate.py` and rewrite `lessons.md` in the same run, so it is able to
un-land a graduation and keep the marker without ever meaning to.

The grammar. One marker, one or more targets, separated by commas:

    - [GRADUATED -> ergonomics_check.MIN_RELIEF_MM] ...
    - [GRADUATED -> gate:"blanket-fillet"] ...
    - [GRADUATED -> gate.check_bill, blocks.add_piece_family] ...

  `module.SYMBOL`  SYMBOL must be defined at the top level of that module:
                   `def SYMBOL(`, `class SYMBOL`, or `SYMBOL = `.
  `module:"..."`   the literal text must appear in that file. This is the form
                   for anything that is not a definition — a lint rule's id, a
                   sentence added to an agent's template — and it is why lint
                   rules carry ids: `gate.LINT_RULES` would stay true after the
                   one rule that mattered was deleted.

A target naming a module this file does not know is a FAILURE, not a skip. A
checker that cannot check something must never report it green; that is the
same rule `gate.py` follows with `unmeasured`.

Prints ALL PASS (improve.py greps for exactly that) or the broken claims.
Exit 0/1.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LESSONS = REPO_ROOT / "board-game" / "lessons.md"
AGENTS = REPO_ROOT / ".claude" / "agents"

#: Where a lesson is allowed to land. Adding a row is how you sanction a new
#: destination; a marker pointing anywhere else fails rather than being
#: ignored, so a typo cannot quietly become an unverified graduation.
MODULES: dict[str, Path] = {
    "gate": HERE / "gate.py",
    "ergonomics_check": HERE / "ergonomics_check.py",
    "rules_check": HERE / "rules_check.py",
    "interference": HERE / "interference.py",
    "pipeline_queue": HERE / "pipeline_queue.py",
    "blocks": REPO_ROOT / "board-game" / "blocks" / "blocks.py",
    "ideator": AGENTS / "board-game-ideator.md",
    "brief_writer": AGENTS / "board-game-brief-writer.md",
    "builder": AGENTS / "board-game-builder.md",
}

MARKER = re.compile(r"\[GRADUATED\s*->\s*([^\]]+)\]")
TARGET = re.compile(r'(\w+)(?:\.(\w+)|:"([^"]*)")')
#: What may legally sit between two targets. Anything else in a marker means
#: it was written in prose, and prose is what this file exists to stop being
#: mistaken for a fix.
SEPARATORS = re.compile(r"^[\s,+]*$")


def _defines(text: str, symbol: str) -> bool:
    return re.search(rf"^(?:def|class)\s+{re.escape(symbol)}\b"
                     rf"|^{re.escape(symbol)}\s*(?::[^=\n]+)?=",
                     text, re.M) is not None


def check_target(module: str, symbol: str | None, literal: str | None) -> str | None:
    """None if the claim holds, else why it does not."""
    path = MODULES.get(module)
    if path is None:
        return (f"'{module}' is not a place a lesson can land — known: "
                f"{', '.join(sorted(MODULES))}")
    if not path.is_file():
        return f"{module} points at {path.relative_to(REPO_ROOT)}, which does not exist"
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel = path.relative_to(REPO_ROOT)
    if symbol is not None:
        if _defines(text, symbol):
            return None
        hint = (' — .md targets need the module:"literal" form'
                if path.suffix == ".md" else "")
        return f"{rel} defines no `{symbol}`{hint}"
    if literal in text:
        return None
    return f'{rel} does not contain "{literal}"'


def verify() -> tuple[list[str], int, int]:
    """(broken claims, graduations checked, lessons still prose)."""
    if not LESSONS.is_file():
        return [f"{LESSONS} is missing"], 0, 0
    broken: list[str] = []
    checked = prose = 0
    for line in LESSONS.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("-") or len(line) <= 40:
            continue
        found = MARKER.search(line)
        if not found:
            prose += 1
            continue
        checked += 1
        body = found.group(1)
        lesson = line.split("]", 1)[-1].strip()[:70]
        targets = list(TARGET.finditer(body))
        leftover = TARGET.sub("", body)
        if not targets or not SEPARATORS.match(leftover):
            broken.append(f'"{lesson}…": marker `{body.strip()}` is prose, not a '
                          f'target — see the grammar in this file')
            continue
        for match in targets:
            why = check_target(match.group(1), match.group(2), match.group(3))
            if why:
                broken.append(f'"{lesson}…": {why}')
    return broken, checked, prose


def main() -> int:
    broken, checked, prose = verify()
    if broken:
        print("GRADUATIONS BROKEN — a lesson claims to be code and is not:")
        for entry in broken:
            print(f"  - {entry}")
        print("\nEither land the fix again, or take the marker off and put the "
              "lesson back in the prompts. Leaving it is the one option that "
              "protects nothing while looking like it does.")
        return 1
    # Not a failure: a lesson that has only cost one build belongs in prose.
    # Printed because it is the honest denominator — how much of what these
    # builds taught is still advice an agent has to remember every time.
    print(f"ALL PASS ({checked} graduation(s) verified, {prose} lesson(s) still "
          f"prose in the prompts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
