import unittest
from unittest.mock import patch

from linux_window_service import friendly_application, parse_wmctrl_line
import platform_utils


class LinuxWindowServiceTests(unittest.TestCase):
    def test_wmctrl_line_keeps_title_but_exposes_application_name(self):
        window = parse_wmctrl_line(
            "0x04600007  0 google-chrome.Google-chrome workstation Secret document - Chrome"
        )

        self.assertIsNotNone(window)
        self.assertEqual(window.application, "Chrome")
        self.assertEqual(window.title, "Secret document - Chrome")

    def test_citrix_window_is_identified_as_vdi(self):
        window = parse_wmctrl_line(
            "0x05200011  0 wfica.Wfica workstation Corporate Desktop"
        )

        self.assertTrue(window.is_vdi)
        self.assertEqual(window.application, "Citrix Workspace")

    def test_friendly_name_does_not_return_full_document_title(self):
        self.assertEqual(
            friendly_application("code.Code", "customer-secrets.js - Visual Studio Code"),
            "VS Code",
        )


class LinuxDesktopIntegrationTests(unittest.TestCase):
    def test_desktop_exec_quotes_interpreter_and_script(self):
        with patch.object(
            platform_utils,
            "get_launch_args",
            return_value=["/opt/Python 3/bin/python", "/home/user/VDI Tools/linux_topdock.py"],
        ):
            value = platform_utils.get_desktop_exec()

        self.assertEqual(
            value,
            '"/opt/Python 3/bin/python" "/home/user/VDI Tools/linux_topdock.py"',
        )


if __name__ == "__main__":
    unittest.main()
