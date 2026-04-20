"""Unit tests - no network or browser needed."""
import sqlite3
import tempfile
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ── compare.py tests ──────────────────────────────────────────────────────────
from compare import _norm, match_key_from_names, compare_moneyline

class TestNorm(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_norm("Boston Bruins"), "boston bruins")

    def test_accent(self):
        # é → e, ä → a etc via NFKD
        self.assertEqual(_norm("Montréal Canadiens"), "montreal canadiens")

    def test_dots_and_spaces(self):
        self.assertEqual(_norm("St. Louis Blues"), "st louis blues")
        self.assertEqual(_norm("St Louis Blues "), "st louis blues")

    def test_match_key_symmetric(self):
        k1 = match_key_from_names("Boston Bruins", "Toronto Maple Leafs")
        k2 = match_key_from_names("Boston Bruins ", "Toronto Maple Leafs")
        self.assertEqual(k1, k2)

class TestCompareMoneyline(unittest.TestCase):
    def _make(self, home, away, ho, ao):
        return {"home_team": home, "away_team": away, "home_odds": ho, "away_odds": ao}

    def test_finds_opportunity(self):
        p = [self._make("Boston Bruins", "Toronto Maple Leafs", 2.00, 1.80)]
        v = [self._make("Boston Bruins", "Toronto Maple Leafs", 2.20, 1.80)]
        result = compare_moneyline(p, v, thr=5.0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["side"], "home")
        self.assertAlmostEqual(result[0]["improvement_pct"], 10.0)

    def test_below_threshold_ignored(self):
        p = [self._make("Boston Bruins", "Toronto Maple Leafs", 2.00, 1.80)]
        v = [self._make("Boston Bruins", "Toronto Maple Leafs", 2.03, 1.80)]
        result = compare_moneyline(p, v, thr=5.0)
        self.assertEqual(len(result), 0)

    def test_accent_names_match(self):
        p = [self._make("Montreal Canadiens", "Ottawa Senators", 2.00, 1.90)]
        v = [self._make("Montréal Canadiens", "Ottawa Senators", 2.20, 1.90)]
        result = compare_moneyline(p, v, thr=5.0)
        self.assertEqual(len(result), 1)

    def test_no_match_different_teams(self):
        p = [self._make("Boston Bruins", "Toronto Maple Leafs", 2.00, 1.80)]
        v = [self._make("New York Rangers", "Washington Capitals", 2.20, 1.80)]
        result = compare_moneyline(p, v, thr=5.0)
        self.assertEqual(len(result), 0)


# ── db.py tests ───────────────────────────────────────────────────────────────
import db as db_module

class TestDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db_module.DB_PATH = Path(self.tmp.name)
        db_module.initialize_db()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_first_notification_should_notify(self):
        self.assertTrue(db_module.should_notify("key1", "home", 10.0))

    def test_after_mark_below_delta_should_not_notify(self):
        db_module.mark_notified("key1", "home", 10.0, "2025-01-01")
        # 14.9 is less than 10.0 + 5.0 = 15.0
        self.assertFalse(db_module.should_notify("key1", "home", 14.9))

    def test_after_mark_above_delta_should_notify(self):
        db_module.mark_notified("key1", "home", 10.0, "2025-01-01")
        # 15.0 == 10.0 + 5.0, should trigger
        self.assertTrue(db_module.should_notify("key1", "home", 15.0))

    def test_different_side_independent(self):
        db_module.mark_notified("key1", "home", 10.0, "2025-01-01")
        self.assertTrue(db_module.should_notify("key1", "away", 10.0))

    def test_upsert_and_wal(self):
        db_module.upsert_event("k", "A", "B", 2.0, 1.8, 2.1, 1.7, "2025-01-01")
        conn = sqlite3.connect(db_module.DB_PATH)
        row = conn.execute("SELECT home_team FROM events WHERE match_key='k'").fetchone()
        conn.close()
        self.assertEqual(row[0], "A")


# ── notifier.py tests ─────────────────────────────────────────────────────────
from notifier import build_message, send_discord_message

class TestNotifier(unittest.TestCase):
    def _ev(self, side="home", imp=8.5):
        return {
            "home_team": "Boston Bruins",
            "away_team": "Toronto Maple Leafs",
            "side": side,
            "pinnacle": 2.00,
            "veikkaus": 2.17,
            "improvement_pct": imp,
        }

    def test_build_message_home(self):
        msg = build_message(self._ev("home"))
        self.assertIn("KOTI", msg)
        self.assertIn("Boston Bruins", msg)
        self.assertIn("8.5%", msg)

    def test_build_message_away(self):
        msg = build_message(self._ev("away"))
        self.assertIn("VIERAS", msg)

    def test_send_no_webhook(self):
        # Should not raise, just log warning
        send_discord_message(None, "test")
        send_discord_message("", "test")

    def test_send_discord_called(self):
        with patch("notifier.requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True)
            send_discord_message("https://discord.com/api/webhooks/fake", "hello")
            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs["json"]
            self.assertEqual(payload["content"], "hello")
            self.assertEqual(payload["username"], "NHL Moneyline Bot")


if __name__ == "__main__":
    unittest.main(verbosity=2)
