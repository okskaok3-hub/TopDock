import time
import unittest
from unittest.mock import patch

import clipboard_paste
from clipboard_paste import ClipboardPaste


class FakeConfig:
    def __init__(self, **values):
        self.values = {
            "paste_hotkey": "ctrl+shift+v",
            "pause_hotkey": "ctrl+shift+p",
            "char_delay": 0.01,
            "press_duration": 0.01,
            "trim_trailing_whitespace": True,
            **values,
        }

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def update(self, values):
        self.values.update(values)


class ClipboardPasteTests(unittest.TestCase):
    def setUp(self):
        self.statuses = []
        self.fake_config = FakeConfig()
        self.config_patch = patch.object(clipboard_paste, "config", self.fake_config)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

        self.add_hotkey_patch = patch.object(
            clipboard_paste.keyboard,
            "add_hotkey",
            side_effect=lambda hotkey, callback: f"handle:{hotkey}",
        )
        self.remove_hotkey_patch = patch.object(clipboard_paste.keyboard, "remove_hotkey")
        self.press_patch = patch.object(clipboard_paste.keyboard, "press")
        self.release_patch = patch.object(clipboard_paste.keyboard, "release")
        self.write_patch = patch.object(clipboard_paste.keyboard, "write")
        self.mocks = []
        for active_patch in (
            self.add_hotkey_patch,
            self.remove_hotkey_patch,
            self.press_patch,
            self.release_patch,
            self.write_patch,
        ):
            self.mocks.append(active_patch.start())
            self.addCleanup(active_patch.stop)
        (
            self.add_hotkey_mock,
            self.remove_hotkey_mock,
            self.press_mock,
            self.release_mock,
            self.write_mock,
        ) = self.mocks

    def make_paste(self):
        return ClipboardPaste(on_status=lambda message, message_type="info": self.statuses.append((message, message_type)))

    @staticmethod
    def wait_until(predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        return predicate()

    def test_second_trigger_is_rejected_before_worker_starts(self):
        paste = self.make_paste()
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="abc"):
            self.assertTrue(paste.trigger_paste())
            self.assertFalse(paste.trigger_paste())
            paste.cancel_paste()
            paste.cleanup()

        self.assertEqual(
            sum("Paste triggered" in message for message, _ in self.statuses),
            1,
        )

    def test_pause_resume_stops_progress_until_resumed(self):
        paste = self.make_paste()
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="abcdef"):
            self.assertTrue(paste.trigger_paste())
            self.assertTrue(paste.pause_resume())
            self.assertTrue(self.wait_until(lambda: paste.get_status() == "Paused"))
            self.assertIn(("Paste paused", "info"), self.statuses)

            self.assertTrue(paste.pause_resume())
            self.assertTrue(self.wait_until(lambda: paste.get_status() == "Ready"))

        self.assertIn(("Paste resumed", "info"), self.statuses)
        self.assertIn(("Paste complete!", "success"), self.statuses)
        paste.cleanup()

    def test_cancel_unblocks_initial_delay_and_finishes(self):
        paste = self.make_paste()
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="abcdef"):
            self.assertTrue(paste.trigger_paste())
            self.assertTrue(paste.cancel_paste())
            self.assertTrue(self.wait_until(lambda: paste.get_status() == "Ready"))

        self.assertTrue(any("Paste cancelled" in message for message, _ in self.statuses))
        paste.cleanup()

    def test_trailing_whitespace_can_be_preserved(self):
        self.fake_config.values["trim_trailing_whitespace"] = False
        paste = self.make_paste()
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="a \n"):
            paste._paste()

        pressed_keys = [call.args[0] for call in self.press_mock.call_args_list]
        self.assertEqual(pressed_keys, ["a", "space", "enter", "shift", "home", "delete"])
        self.assertIn(("Paste complete!", "success"), self.statuses)

    def test_newline_clears_editor_generated_indentation(self):
        paste = self.make_paste()
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="a\n  b"):
            paste._paste()

        pressed_keys = [call.args[0] for call in self.press_mock.call_args_list]
        self.assertEqual(
            pressed_keys,
            ["a", "enter", "shift", "home", "delete", "space", "space", "b"],
        )
        self.assertGreaterEqual(
            sum(call.args[0] == "shift" for call in self.release_mock.call_args_list),
            2,
        )

    def test_unsupported_symbols_are_skipped_and_typing_continues(self):
        paste = self.make_paste()
        self.write_mock.side_effect = ValueError("unsupported")
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="a→€😀b"):
            paste._paste()

        self.assertEqual([call.args[0] for call in self.press_mock.call_args_list], ["a", "b"])
        self.write_mock.assert_not_called()
        self.assertIn(("Paste complete; skipped 3 unsupported symbols", "warning"), self.statuses)

    def test_cleanup_cancels_active_worker(self):
        paste = self.make_paste()
        with patch.object(clipboard_paste.pyperclip, "paste", return_value="abcdef"):
            paste.trigger_paste()
            paste.cleanup()

        self.assertEqual(paste.get_status(), "Ready")

    def test_hotkey_registration_failure_cleans_partial_registration(self):
        self.add_hotkey_mock.side_effect = ["paste-handle", RuntimeError("permission denied")]
        paste = self.make_paste()

        self.assertIsNone(paste.hotkey_handler)
        self.assertIsNone(paste.pause_handler)
        self.assertTrue(any("registration failed" in message for message, _ in self.statuses))
        self.remove_hotkey_mock.assert_called_once_with("paste-handle")

    def test_pause_hotkey_conflict_is_rejected(self):
        self.fake_config.values["pause_hotkey"] = "ctrl+shift+v"
        paste = self.make_paste()

        self.assertIsNone(paste.hotkey_handler)
        self.assertTrue(any("must be different" in message for message, _ in self.statuses))


if __name__ == "__main__":
    unittest.main()
