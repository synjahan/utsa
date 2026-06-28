"""
tests.py
--------
Unit tests for telegram_forwarder.py

Run with:
    python3 -m pytest tests.py -v
    # or without pytest:
    python3 tests.py

No network or Telegram connection needed — all external calls are mocked.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import os

# ── Import the module under test ──────────────────────────────────────────────
# Patch heavy imports before they're loaded so tests work without
# telethon/requests installed in a CI environment
sys.modules.setdefault("telethon", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

import importlib
import types

# Provide a stub load_dotenv so the module-level call is a no-op
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv_stub

import telegram_forwarder as tf


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_message(
    id="1510986552103145714",
    content="Hello world",
    created="2026-06-01T12:41:06.794000+00:00",
    display="Syn",
    username="inhaleexhalebreathe",
    author_id="1098785229889601556",
):
    return {
        "id": id,
        "content": content,
        "createdAt": created,
        "editedAt": None,
        "author": {
            "id": author_id,
            "username": username,
            "displayName": display,
            "bot": False,
        },
        "attachments": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# extract_items
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractItems(unittest.TestCase):

    def test_messages_key(self):
        """Standard API shape: {"messages": [...]}"""
        msg = make_message()
        data = {"messages": [msg]}
        result = tf.extract_items(data, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], msg["id"])

    def test_data_key(self):
        msg = make_message()
        result = tf.extract_items({"data": [msg]}, None)
        self.assertEqual(len(result), 1)

    def test_top_level_list(self):
        msgs = [make_message(id="1"), make_message(id="2")]
        result = tf.extract_items(msgs, None)
        self.assertEqual(len(result), 2)

    def test_plain_string_wrapped(self):
        result = tf.extract_items("just a string", None)
        self.assertEqual(result, [{"text": "just a string"}])

    def test_string_items_in_list_wrapped(self):
        result = tf.extract_items(["a", "b"], None)
        self.assertEqual(result, [{"text": "a"}, {"text": "b"}])

    def test_custom_msg_field(self):
        data = {"custom": [make_message()]}
        result = tf.extract_items(data, "custom")
        self.assertEqual(len(result), 1)

    def test_empty_list(self):
        result = tf.extract_items({"messages": []}, None)
        self.assertEqual(result, [])

    def test_single_message_dict(self):
        data = {"message": "hello"}
        result = tf.extract_items(data, None)
        self.assertEqual(len(result), 1)

    def test_filters_out_falsy(self):
        result = tf.extract_items([None, "", make_message()], None)
        # None and "" are falsy and should be dropped; make_message() kept
        self.assertEqual(len(result), 1)


# ─────────────────────────────────────────────────────────────────────────────
# item_id
# ─────────────────────────────────────────────────────────────────────────────

class TestItemId(unittest.TestCase):

    def test_returns_string(self):
        item = make_message(id="123456789012345678")
        self.assertEqual(tf.item_id(item, "id"), "123456789012345678")

    def test_integer_id_converted(self):
        self.assertEqual(tf.item_id({"id": 42}, "id"), "42")

    def test_missing_id_returns_none(self):
        self.assertIsNone(tf.item_id({}, "id"))

    def test_custom_id_field(self):
        self.assertEqual(tf.item_id({"snowflake": "999"}, "snowflake"), "999")


# ─────────────────────────────────────────────────────────────────────────────
# item_text
# ─────────────────────────────────────────────────────────────────────────────

class TestItemText(unittest.TestCase):

    def _call(self, item, msg_field=None):
        return tf.item_text(item, msg_field, user_api_url="", api_key="", user_map_file="")

    def test_formats_correctly(self):
        item = make_message(content="Hello", created="2026-06-01T12:41:06.794000+00:00", display="Syn")
        result = self._call(item)
        self.assertEqual(result, "Syn - 2026-06-01 12:41:06: Hello")

    def test_empty_content_returns_none(self):
        item = make_message(content="")
        self.assertIsNone(self._call(item))

    def test_whitespace_only_returns_none(self):
        item = make_message(content="   ")
        self.assertIsNone(self._call(item))

    def test_missing_content_returns_none(self):
        item = make_message()
        del item["content"]
        self.assertIsNone(self._call(item))

    def test_no_timestamp_still_formats(self):
        item = make_message(content="Hi", created="")
        result = self._call(item)
        self.assertEqual(result, "Syn: Hi")

    def test_falls_back_to_username_when_no_displayname(self):
        item = make_message(content="Hi", display="")
        result = self._call(item)
        self.assertIn("inhaleexhalebreathe", result)

    def test_falls_back_to_unknown_when_no_author(self):
        item = make_message(content="Hi")
        item["author"] = {}
        result = self._call(item)
        self.assertIn("Unknown", result)

    def test_timestamp_trimmed(self):
        item = make_message(content="Hi", created="2026-06-01T12:41:06.794000+00:00")
        result = self._call(item)
        self.assertIn("2026-06-01 12:41:06", result)
        self.assertNotIn("794000", result)
        self.assertNotIn("+00:00", result)


# ─────────────────────────────────────────────────────────────────────────────
# resolve_mentions
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveMentions(unittest.TestCase):

    def setUp(self):
        # Reset the global user_map before each test
        tf.user_map.clear()

    def _call(self, content):
        return tf.resolve_mentions(content, user_api_url="", api_key="", user_map_file="")

    def test_known_id_replaced_with_displayname(self):
        tf.user_map["123456789012345678"] = {"displayName": "Alice", "username": "alice"}
        result = self._call("Hello <@123456789012345678>!")
        self.assertEqual(result, "Hello @Alice!")

    def test_falls_back_to_username(self):
        tf.user_map["123456789012345678"] = {"displayName": "", "username": "alice"}
        result = self._call("<@123456789012345678>")
        self.assertEqual(result, "@alice")

    def test_unknown_id_left_as_is_when_no_api_url(self):
        # No user_api_url set, fetch will fail silently, original kept
        result = self._call("<@999999999999999999>")
        self.assertEqual(result, "<@999999999999999999>")

    def test_too_short_id_not_replaced(self):
        # 16 digits — below the 17-19 range
        result = self._call("<@1234567890123456>")
        self.assertEqual(result, "<@1234567890123456>")

    def test_too_long_id_not_replaced(self):
        # 20 digits — above the range
        result = self._call("<@12345678901234567890>")
        self.assertEqual(result, "<@12345678901234567890>")

    def test_17_digit_id_matched(self):
        tf.user_map["12345678901234567"] = {"displayName": "Bob", "username": "bob"}
        result = self._call("<@12345678901234567>")
        self.assertEqual(result, "@Bob")

    def test_19_digit_id_matched(self):
        tf.user_map["1234567890123456789"] = {"displayName": "Eve", "username": "eve"}
        result = self._call("<@1234567890123456789>")
        self.assertEqual(result, "@Eve")

    def test_multiple_mentions(self):
        tf.user_map["123456789012345678"] = {"displayName": "Alice", "username": "alice"}
        tf.user_map["987654321098765432"] = {"displayName": "Bob", "username": "bob"}
        result = self._call("<@123456789012345678> and <@987654321098765432>")
        self.assertEqual(result, "@Alice and @Bob")

    def test_no_mentions_unchanged(self):
        result = self._call("No mentions here.")
        self.assertEqual(result, "No mentions here.")

    def test_plain_number_not_replaced(self):
        # A bare number without <@...> should not be touched
        result = self._call("There are 123456789012345678 reasons.")
        self.assertEqual(result, "There are 123456789012345678 reasons.")


# ─────────────────────────────────────────────────────────────────────────────
# update_user_map
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateUserMap(unittest.TestCase):

    def setUp(self):
        tf.user_map.clear()

    def test_new_author_added(self):
        item = make_message()
        changed = tf.update_user_map(item)
        self.assertTrue(changed)
        self.assertIn("1098785229889601556", tf.user_map)

    def test_same_author_no_change(self):
        item = make_message()
        tf.update_user_map(item)
        changed = tf.update_user_map(item)
        self.assertFalse(changed)

    def test_updated_displayname_detected(self):
        item = make_message(display="Syn")
        tf.update_user_map(item)
        item2 = make_message(display="SynUpdated")
        changed = tf.update_user_map(item2)
        self.assertTrue(changed)
        self.assertEqual(tf.user_map["1098785229889601556"]["displayName"], "SynUpdated")

    def test_no_author_id_returns_false(self):
        item = {"content": "hi", "author": {}}
        changed = tf.update_user_map(item)
        self.assertFalse(changed)

    def test_no_author_key_returns_false(self):
        item = {"content": "hi"}
        changed = tf.update_user_map(item)
        self.assertFalse(changed)


# ─────────────────────────────────────────────────────────────────────────────
# load_last_id / save_last_id
# ─────────────────────────────────────────────────────────────────────────────

class TestCursorPersistence(unittest.TestCase):

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".last_message_id"
            tf.save_last_id(path, "1511982165372698675")
            result = tf.load_last_id(path)
            self.assertEqual(result, "1511982165372698675")

    def test_load_missing_file_returns_none(self):
        path = Path("/tmp/nonexistent_cursor_file_xyz")
        self.assertIsNone(tf.load_last_id(path))

    def test_load_empty_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".last_message_id"
            path.write_text("   ")
            self.assertIsNone(tf.load_last_id(path))

    def test_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".last_message_id"
            tf.save_last_id(path, "111")
            tf.save_last_id(path, "222")
            self.assertEqual(tf.load_last_id(path), "222")


# ─────────────────────────────────────────────────────────────────────────────
# load_user_map / save_user_map
# ─────────────────────────────────────────────────────────────────────────────

class TestUserMapPersistence(unittest.TestCase):

    def setUp(self):
        tf.user_map.clear()

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / ".user_map.json")
            tf.user_map["123"] = {"displayName": "Alice", "username": "alice"}
            tf.save_user_map(path)
            tf.user_map.clear()
            tf.load_user_map(path)
            self.assertEqual(tf.user_map["123"]["displayName"], "Alice")

    def test_load_missing_file_starts_fresh(self):
        tf.load_user_map("/tmp/no_such_file_xyz.json")
        self.assertEqual(tf.user_map, {})

    def test_save_is_atomic(self):
        """Tmp file should not exist after save completes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / ".user_map.json")
            tf.user_map["1"] = {"displayName": "X", "username": "x"}
            tf.save_user_map(path)
            tmp = str(Path(tmpdir) / ".user_map.tmp")
            self.assertFalse(os.path.exists(tmp))


# ─────────────────────────────────────────────────────────────────────────────
# poll_api (mocked network)
# ─────────────────────────────────────────────────────────────────────────────

class TestPollApi(unittest.TestCase):

    @patch("telegram_forwarder.requests.get")
    def test_sends_correct_headers_and_params(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"messages": []}
        mock_get.return_value = mock_resp

        tf.poll_api("https://api.example.com/messages", "mykey", after="123", limit=50)

        call_kwargs = mock_get.call_args
        self.assertEqual(call_kwargs[1]["headers"]["x-api-key"], "mykey")
        self.assertEqual(call_kwargs[1]["params"]["limit"], 50)
        self.assertEqual(call_kwargs[1]["params"]["after"], "123")

    @patch("telegram_forwarder.requests.get")
    def test_no_after_param_on_first_run(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        tf.poll_api("https://api.example.com/messages", "key", after=None, limit=100)

        params = mock_get.call_args[1]["params"]
        self.assertNotIn("after", params)

    @patch("telegram_forwarder.requests.get")
    def test_returns_none_on_error(self, mock_get):
        mock_get.side_effect = tf.requests.exceptions.ConnectionError("timeout")
        result = tf.poll_api("https://api.example.com", "key", after=None, limit=100)
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
