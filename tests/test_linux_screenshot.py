import unittest

from linux_screenshot_service import LinuxScreenshotService


class FakeImage:
    width, height = 640, 360
    size = (640, 360)
    def save(self, target, format=None):
        if format != "PNG":
            raise AssertionError("Screenshot must be encoded as PNG")
        target.write(b"PNG-DATA")


class FakeResult:
    returncode = 0
    stderr = b""


class LinuxScreenshotServiceTests(unittest.TestCase):
    def test_capture_copies_png_to_xclip(self):
        calls = []

        def fake_runner(arguments, **kwargs):
            calls.append((arguments, kwargs))
            return FakeResult()

        service = LinuxScreenshotService(
            screenshotter=FakeImage(),
            runner=fake_runner,
            command_finder=lambda command: "/usr/bin/xclip" if command == "xclip" else None,
        )

        result = service.capture_to_clipboard()

        self.assertTrue(result.success)
        self.assertEqual(calls[0][0], ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"])
        self.assertEqual(calls[0][1]["input"], b"PNG-DATA")

    def test_missing_xclip_has_actionable_error(self):
        service = LinuxScreenshotService(command_finder=lambda _command: None)
        result = service.capture_to_clipboard()

        self.assertFalse(result.success)
        self.assertIn("xclip", result.message)

    def test_selected_region_is_forwarded_to_capture_backend(self):
        regions = []

        def screenshotter(region):
            regions.append(region)
            return FakeImage()

        service = LinuxScreenshotService(
            screenshotter=screenshotter,
            runner=lambda _arguments, **_kwargs: FakeResult(),
            command_finder=lambda _command: "/usr/bin/xclip",
        )

        result = service.capture_to_clipboard(region=(40, 80, 640, 360))

        self.assertTrue(result.success)
        self.assertEqual(regions, [(40, 80, 640, 360)])


if __name__ == "__main__":
    unittest.main()
