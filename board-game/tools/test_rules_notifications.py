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
import animation_gate  # noqa: E402
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


def approve_animation(home: Path, payload: bytes = b"video") -> Path:
    video = home / animation_gate.VIDEO_REL
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(payload)
    video_hash = animation_gate.sha256(video)
    manifest = {
        "idea_sha256": animation_gate.sha256(home / "idea.json"),
        "video_sha256": video_hash,
        "video": str(animation_gate.VIDEO_REL),
    }
    (home / animation_gate.MANIFEST_REL).write_text(
        json.dumps(manifest), encoding="utf-8")
    (home / animation_gate.REVIEW_REL).write_text(
        f"Verdict: PASS\nVideo SHA256: {video_hash}\n", encoding="utf-8")
    return video


class ReworkBudgetTests(unittest.TestCase):
    def test_budget_is_granted_and_next_failure_kills(self) -> None:
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
                slug="fixture", stage="lens_rules", reason="finding",
                disposition="rework")
            local_log = root / "journal.jsonl"
            with patch.object(pipeline_queue, "QUEUE", queue), \
                    patch.object(pipeline_queue, "LOCK", root / ".lock"), \
                    patch.object(pipeline_queue, "IDEAS", ideas), \
                    patch.object(journal, "JOURNAL_LOG", local_log):
                for number in range(1, pipeline_queue.REWORK_BUDGET + 1):
                    current = idea(concept=f"iteration {number}")
                    (home / "idea.json").write_text(
                        json.dumps(current), encoding="utf-8")
                    self.assertEqual(pipeline_queue.cmd_gate_rework(args), 0)
                    snapshot = json.loads(
                        (home / journal.SNAPSHOT_NAME).read_text(encoding="utf-8"))
                    self.assertEqual(snapshot["rework_number"], number)
                    self.assertEqual(snapshot["idea"], current)

                data = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["ideas"]["fixture"]["rework_used"],
                    pipeline_queue.REWORK_BUDGET)
                self.assertEqual(data["ideas"]["fixture"]["state"], "proposed")
                self.assertEqual(pipeline_queue.cmd_gate_rework(args), 1)
                data = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(data["ideas"]["fixture"]["state"], "killed")


    def _clarify_args(self, stage="lens_rules"):
        return SimpleNamespace(
            slug="fixture", stage=stage, reason="ambiguity",
            disposition="clarify")

    def test_clarify_rounds_have_their_own_budget(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue = root / "QUEUE.json"
            ideas = root / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            queue.write_text(json.dumps({"ideas": {"fixture": {
                "slug": "fixture", "title": "Fixture", "state": "proposed",
                "rework_used": 0, "clarify_used": 0, "repairs_used": 0,
                "log": [],
            }}}), encoding="utf-8")
            with patch.object(pipeline_queue, "QUEUE", queue), \
                    patch.object(pipeline_queue, "LOCK", root / ".lock"), \
                    patch.object(pipeline_queue, "IDEAS", ideas), \
                    patch.object(journal, "JOURNAL_LOG", root / "journal.jsonl"):
                # Three clarify rounds over the same mechanic surface: only
                # the rule text moves, so each stays a clarification.
                for number in range(1, pipeline_queue.CLARIFY_BUDGET + 1):
                    (home / "idea.json").write_text(json.dumps(
                        idea(turn=f"PLACE a token, step {number}.")),
                        encoding="utf-8")
                    self.assertEqual(
                        pipeline_queue.cmd_gate_rework(self._clarify_args()), 0)
                    snapshot = json.loads(
                        (home / journal.SNAPSHOT_NAME).read_text(encoding="utf-8"))
                    self.assertEqual(snapshot["disposition"], "clarify")
                    self.assertEqual(snapshot["rework_number"], number)
                    self.assertEqual(snapshot["mech_surface"],
                                     pipeline_queue.mech_surface(idea()))

                data = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["ideas"]["fixture"]["clarify_used"],
                    pipeline_queue.CLARIFY_BUDGET)
                self.assertEqual(data["ideas"]["fixture"]["rework_used"], 0)
                # The clarify budget is exhausted: the next clarify kills, and
                # the rework budget has been left completely untouched.
                self.assertEqual(
                    pipeline_queue.cmd_gate_rework(self._clarify_args()), 1)
                data = json.loads(queue.read_text(encoding="utf-8"))
                self.assertEqual(data["ideas"]["fixture"]["state"], "killed")
                self.assertEqual(data["ideas"]["fixture"]["rework_used"], 0)
                self.assertIn("clarify budget exhausted",
                              data["ideas"]["fixture"]["kill_reason"])

    def test_clarify_that_changes_the_mechanic_pays_as_rework(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue = root / "QUEUE.json"
            ideas = root / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            queue.write_text(json.dumps({"ideas": {"fixture": {
                "slug": "fixture", "title": "Fixture", "state": "proposed",
                "rework_used": 0, "clarify_used": 0, "repairs_used": 0,
                "log": [],
            }}}), encoding="utf-8")
            with patch.object(pipeline_queue, "QUEUE", queue), \
                    patch.object(pipeline_queue, "LOCK", root / ".lock"), \
                    patch.object(pipeline_queue, "IDEAS", ideas), \
                    patch.object(journal, "JOURNAL_LOG", root / "journal.jsonl"):
                (home / "idea.json").write_text(json.dumps(idea()),
                                                encoding="utf-8")
                self.assertEqual(
                    pipeline_queue.cmd_gate_rework(self._clarify_args()), 0)

                # The "clarification" rewrote the winner. The queue settles
                # that on the next round and charges the rework budget.
                cheated = idea()
                cheated["rules"]["win"] = {
                    "text": "Fewest tokens wins.", "uses": ["token"]}
                (home / "idea.json").write_text(json.dumps(cheated),
                                                encoding="utf-8")
                self.assertEqual(pipeline_queue.cmd_gate_rework(
                    SimpleNamespace(slug="fixture", stage="lens_rules",
                                    reason="defect", disposition="rework")), 0)

                data = json.loads(queue.read_text(encoding="utf-8"))
                fixture = data["ideas"]["fixture"]
                # The laundered round was charged as rework 1, and the honest
                # rework just granted is rework 2: two rounds for two failed
                # gates, nothing free.
                self.assertEqual(fixture["rework_used"], 2)
                self.assertEqual(fixture["clarify_used"], 0)
                notes = [entry["note"] for entry in fixture["log"]]
                self.assertIn(
                    "clarify round converted to rework: the mechanic surface "
                    f"changed during a clarification round — "
                    f"1/{pipeline_queue.REWORK_BUDGET} reworks now spent",
                    notes)
                self.assertIn(f"rework round 2/{pipeline_queue.REWORK_BUDGET}"
                              " (lens_rules): defect", notes)

    def test_conversion_fires_when_leaving_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue = root / "QUEUE.json"
            ideas = root / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            queue.write_text(json.dumps({"ideas": {"fixture": {
                "slug": "fixture", "title": "Fixture", "state": "proposed",
                "rework_used": 0, "clarify_used": 0, "repairs_used": 0,
                "log": [],
            }}}), encoding="utf-8")
            (home / "idea.json").write_text(json.dumps(idea()), encoding="utf-8")
            (home / "review_playtest.md").write_text("Verdict: PASS\n",
                                                     encoding="utf-8")
            with patch.object(pipeline_queue, "QUEUE", queue), \
                    patch.object(pipeline_queue, "LOCK", root / ".lock"), \
                    patch.object(pipeline_queue, "IDEAS", ideas), \
                    patch.object(journal, "JOURNAL_LOG", root / "journal.jsonl"):
                self.assertEqual(
                    pipeline_queue.cmd_gate_rework(self._clarify_args()), 0)
                cheated = idea()
                cheated["components"][0]["qty"] = 24
                (home / "idea.json").write_text(json.dumps(cheated),
                                                encoding="utf-8")
                (home / "review_playtest.md").write_text("Verdict: PASS\n",
                                                         encoding="utf-8")
                self.assertEqual(pipeline_queue.cmd_advance(
                    SimpleNamespace(slug="fixture", to="rules_ok", note=None)), 0)

                data = json.loads(queue.read_text(encoding="utf-8"))
                fixture = data["ideas"]["fixture"]
                self.assertEqual(fixture["rework_used"], 1)
                self.assertEqual(fixture["clarify_used"], 0)


class RulesReadyTests(unittest.TestCase):
    def test_rework_bolds_changed_blocks_only(self) -> None:
        previous = idea()
        current = idea(turn="MOVE one token.")
        rendered = "\n\n".join(
            journal.render_rules_ready(current, previous, 2))
        self.assertIn(f"REWORK 2/{pipeline_queue.REWORK_BUDGET}", rendered)
        self.assertIn("<b>TURN 1\nMOVE one token.</b>", rendered)
        self.assertIn("SETUP 1\nGive each player tokens.", rendered)
        self.assertNotIn("<b>SETUP 1", rendered)

    def test_phase_label_follows_the_rounds_disposition(self) -> None:
        previous = idea()
        current = idea(turn="PLACE a token, if you can.")
        # A clarify round is labelled CLARIFY against the clarify budget, and
        # a rework round REWORK against the rework budget, so the number in a
        # notification always matches the counter it is drawing down.
        clarify = "\n\n".join(
            journal.render_rules_ready(current, previous, 2, "clarify"))
        self.assertIn(f"CLARIFY 2/{pipeline_queue.CLARIFY_BUDGET}", clarify)
        self.assertNotIn("REWORK", clarify)
        rework = "\n\n".join(
            journal.render_rules_ready(current, previous, 2, "rework"))
        self.assertIn(f"REWORK 2/{pipeline_queue.REWORK_BUDGET}", rework)
        # A snapshot from before the field existed reads as a rework round,
        # so an old notice is never mislabelled as a clarify.
        legacy = "\n\n".join(journal.render_rules_ready(current, previous, 2))
        self.assertIn(f"REWORK 2/{pipeline_queue.REWORK_BUDGET}", legacy)

        caption = journal.render_video_caption(
            current, previous, 2, "clarify")
        self.assertIn(f"CLARIFY 2/{pipeline_queue.CLARIFY_BUDGET}", caption)

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
            video = approve_animation(home)
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
                self.assertEqual(sent[0][1], {
                    "video": video,
                    "chat": "journal-chat",
                    "parse_mode": "HTML",
                })
                self.assertTrue(all(kwargs == {
                    "chat": "journal-chat", "parse_mode": "HTML"
                } for _, kwargs in sent[1:]))
                self.assertEqual(journal.cmd_rules_ready(args), 0)
                self.assertEqual(len(sent), first_count)

                approve_animation(home, b"corrected video")
                self.assertEqual(journal.cmd_rules_ready(args), 0)
                self.assertGreater(len(sent), first_count)

    def test_rules_ready_refuses_an_unpassed_pre_table_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ideas = Path(raw) / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            (home / "idea.json").write_text(json.dumps(idea()), encoding="utf-8")
            with patch.object(journal, "IDEAS", ideas):
                with self.assertRaisesRegex(SystemExit, "review_rules.md is missing"):
                    journal.cmd_rules_ready(SimpleNamespace(slug="fixture"))

    def test_rules_ready_refuses_missing_animation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ideas = Path(raw) / "ideas"
            home = ideas / "fixture"
            home.mkdir(parents=True)
            (home / "idea.json").write_text(json.dumps(idea()), encoding="utf-8")
            (home / "review_rules.md").write_text("Verdict: PASS\n", encoding="utf-8")
            (home / "playtest.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            with patch.object(journal, "IDEAS", ideas):
                with self.assertRaisesRegex(SystemExit, "animation/rules.mp4 is missing"):
                    journal.cmd_rules_ready(SimpleNamespace(slug="fixture"))

    def test_animation_review_is_bound_to_video_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            (home / "idea.json").write_text(json.dumps(idea()), encoding="utf-8")
            video = approve_animation(home)
            video.write_bytes(b"changed after review")
            failure, _ = animation_gate.evidence(home)
            self.assertIn("manifest does not match animation/rules.mp4", failure)

    def test_every_rendered_message_fits_without_truncation(self) -> None:
        long_text = "<&>" * 3000
        current = idea(concept=long_text)
        chunks = journal.render_rules_ready(current)
        self.assertTrue(all(len(chunk) <= journal.MESSAGE_LIMIT for chunk in chunks))
        self.assertEqual("".join(journal._escaped_segments(long_text)),
                         html.escape(long_text))
        caption = journal.render_video_caption(current)
        self.assertLessEqual(len(caption), 1000)
        self.assertNotRegex(caption, r"&(?!amp;|lt;|gt;|quot;|#x27;)")


if __name__ == "__main__":
    unittest.main()
