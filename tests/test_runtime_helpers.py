import unittest

from auto_clicker import AutoClicker
from startup_diagnostics import check_required_modules, format_tk_error


class DiagnosticsTests(unittest.TestCase):
    def test_missing_modules_are_reported(self):
        def fake_import(name):
            if name == "keyboard":
                raise ModuleNotFoundError("No module named 'keyboard'")
            return object()

        issues = check_required_modules(
            required_modules={"keyboard": "keyboard", "pyperclip": "pyperclip"},
            importer=fake_import,
        )

        self.assertEqual(len(issues), 1)
        self.assertIn("keyboard", issues[0])

    def test_tk_error_is_formatted_usefully(self):
        message = format_tk_error(RuntimeError("Can't find a usable init.tcl"))
        self.assertIn("Tcl/Tk", message)


class AutoClickerApiTests(unittest.TestCase):
    def test_toggle_requires_area_selection(self):
        messages = []
        clicker = AutoClicker.__new__(AutoClicker)
        clicker.selection_coords = None
        clicker.clicking = False
        clicker.status_window = None
        clicker.on_status = lambda msg, msg_type: messages.append((msg, msg_type))

        result = AutoClicker.toggle(clicker)

        self.assertFalse(result)
        self.assertEqual(messages, [("Select an area first", "warning")])


if __name__ == "__main__":
    unittest.main()
