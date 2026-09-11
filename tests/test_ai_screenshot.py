import unittest

from ai_screenshot import (
    build_gemini_payload,
    build_openai_payload,
    extract_gemini_text,
    extract_openai_text,
)


class AIScreenshotPayloadTests(unittest.TestCase):
    def test_openai_payload_includes_text_and_image(self):
        payload = build_openai_payload(
            "gpt-4.1-mini",
            "System prompt",
            "What is visible?",
            b"png-bytes",
        )

        self.assertEqual(payload["model"], "gpt-4.1-mini")
        self.assertEqual(payload["instructions"], "System prompt")
        content = payload["input"][0]["content"]
        self.assertEqual(content[0]["type"], "input_text")
        self.assertEqual(content[0]["text"], "What is visible?")
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))

    def test_gemini_payload_includes_inline_image(self):
        payload = build_gemini_payload("System prompt", "Summarize", b"png-bytes")

        self.assertEqual(payload["system_instruction"]["parts"][0]["text"], "System prompt")
        parts = payload["contents"][0]["parts"]
        self.assertEqual(parts[0]["text"], "Summarize")
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "image/png")
        self.assertTrue(parts[1]["inline_data"]["data"])

    def test_extract_openai_text_prefers_top_level_field(self):
        self.assertEqual(
            extract_openai_text({"output_text": "Answer"}),
            "Answer",
        )

    def test_extract_gemini_text_reads_candidate_parts(self):
        self.assertEqual(
            extract_gemini_text(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "Line one"},
                                    {"text": "Line two"},
                                ]
                            }
                        }
                    ]
                }
            ),
            "Line one\n\nLine two",
        )


if __name__ == "__main__":
    unittest.main()
