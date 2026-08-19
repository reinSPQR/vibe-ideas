#!/usr/bin/env python3
"""Regression tests for rules rework budgeting and journal notifications."""
from __future__ import annotations

import html
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import journal  # noqa: E402
import pipeline_queue  # noqa: E402


def idea(concept: str = "Original", turn: str = "PLACE a token.") -> dict:
    return {
        "slug": "fixture",
        "title": "Fixture",
        "concept": concept,
        "playtime_min": 20,
        "players": {"min": 2, "max": 4},
        "action_types": ["PLACE"],
        "components": [{"name": "token", "qty": 12}],
        "rules": {
            "setup": [{"text": "Give each player tokens.", "uses": ["token"]}],
            "turn": [{"text": turn, "uses": ["token"]}],
            "end": [{"text": "End when tokens run out.", "uses": ["token"]}],
            "win": {"text": "Most tokens wins.", "uses": ["token"]},
        },
    }


class ReworkBudgetTests(unittest.TestCase):
    def test_ten_reworks_are_granted_and_eleventh_failure_kills(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue = root / "QUEUE.json"
            ideas = root / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            queue.write_text(json.dumps({"ideas": {"fixture": {
                "slug": "fixture", "title": "Fixture", "state": "proposed",
                "rework_used": 0, "repairs_used": 0, "log": [],
            }}}), encoding="utf-8")
            args = SimpleNamespace(
                slug="fixture", stage="lens_rules", reason="finding")
            local_log = root / "journal.jsonl"
            with patch.object(pipeline_queue, "QUEUE", queue), \
                    patch.object(pipeline_queue, "LOCK", root / ".lock"), \
                    patch.object(pipeline_queue, "IDEAS", ideas), \
                    patch.object(journal, "JOURNAL_LOG", local_log):
                for number in range(1, 11):
                    current = idea(concept=f"iteration {number}")
                    (home / "idea.json").write_text(
                        json.dumps(current), encoding="utf-8")
                    self.assertEqual(pipeline_queue.cmd_gate_rework(args), 0)
                    snapshot = json.loads(
                        (home / journal.SNAPSHOT_NAME).read_text(encoding="utf-8"))
                    self.assertEqual(snapshot["rework_number"], number)
                    self.assertEqual(snapshot["idea"], current)

                data = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(data["ideas"]["fixture"]["rework_used"], 10)
                self.assertEqual(data["ideas"]["fixture"]["state"], "proposed")
                self.assertEqual(pipeline_queue.cmd_gate_rework(args), 1)
                data = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(data["ideas"]["fixture"]["state"], "killed")


class RulesReadyTests(unittest.TestCase):
    def test_rework_bolds_changed_blocks_only(self) -> None:
        previous = idea()
        current = idea(turn="MOVE one token.")
        rendered = "\n\n".join(journal.render_rules_ready(current, previous, 4))
        self.assertIn("REWORK 4/10", rendered)
        self.assertIn("<b>TURN 1\nMOVE one token.</b>", rendered)
        self.assertIn("SETUP 1\nGive each player tokens.", rendered)
        self.assertNotIn("<b>SETUP 1", rendered)

    def test_removed_rule_is_bold(self) -> None:
        previous = idea()
        previous["rules"]["turn"].append(
            {"text": "PASS if blocked.", "uses": []})
        rendered = "\n\n".join(journal.render_rules_ready(idea(), previous, 2))
        self.assertIn("<b>REMOVED TURN 2\nPASS if blocked.</b>", rendered)

    def test_append_is_local_and_rules_ready_is_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            ideas = root / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            (home / "idea.json").write_text(json.dumps(idea()), encoding="utf-8")
            (home / "review_rules.md").write_text(
                "Verdict: PASS\n", encoding="utf-8")
            (home / "playtest.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            sent: list[tuple[str, dict]] = []

            class FakeTelegram:
                @staticmethod
                def load_env() -> None:
                    pass

                @staticmethod
                def send(text: str, **kwargs) -> None:
                    sent.append((text, kwargs))

            with patch.object(journal, "IDEAS", ideas), \
                    patch.object(journal, "JOURNAL_LOG", root / "journal.jsonl"), \
                    patch.dict(sys.modules, {"telegram": FakeTelegram}), \
                    patch.dict(os.environ, {
                        "TELEGRAM_BOT_TOKEN": "token",
                        "TELEGRAM_CHAT_JOURNAL": "journal-chat",
                    }, clear=False):
                journal.append("fixture", "gate", "test", "ordinary event")
                self.assertEqual(sent, [])
                args = SimpleNamespace(slug="fixture")
                self.assertEqual(journal.cmd_rules_ready(args), 0)
                first_count = len(sent)
                self.assertGreater(first_count, 0)
                self.assertTrue(all(
                    kwargs == {"chat": "journal-chat", "parse_mode": "HTML"}
                    for _, kwargs in sent))
                self.assertEqual(journal.cmd_rules_ready(args), 0)
                self.assertEqual(len(sent), first_count)

    def test_rules_ready_refuses_an_unpassed_pre_table_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ideas = Path(raw) / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            (home / "idea.json").write_text(json.dumps(idea()), encoding="utf-8")
            with patch.object(journal, "IDEAS", ideas):
                with self.assertRaisesRegex(SystemExit, "review_rules.md is missing"):
                    journal.cmd_rules_ready(SimpleNamespace(slug="fixture"))

    def test_every_rendered_message_fits_without_truncation(self) -> None:
        long_text = "<&>" * 3000
        current = idea(concept=long_text)
        chunks = journal.render_rules_ready(current)
        self.assertTrue(all(len(chunk) <= journal.MESSAGE_LIMIT for chunk in chunks))
        self.assertEqual("".join(journal._escaped_segments(long_text)),
                         html.escape(long_text))


if __name__ == "__main__":
    unittest.main()
