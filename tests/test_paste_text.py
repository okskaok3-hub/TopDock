import unittest
from paste_text import prepare_vdi_text


class PasteTextTests(unittest.TestCase):
    def test_symbols_do_not_interrupt_surrounding_code(self):
        text, skipped = prepare_vdi_text('const x = "A→B";\r\n\treturn x; 😀')
        self.assertEqual(text, 'const x = "AB";\n\treturn x; ')
        self.assertEqual(skipped, 2)

    def test_all_ascii_code_is_preserved(self):
        text = "".join(chr(i) for i in range(32, 127)) + "\n\t"
        self.assertEqual(prepare_vdi_text(text), (text, 0))

    def test_controls_are_skipped_not_executed(self):
        self.assertEqual(prepare_vdi_text('ab\b\x1b\x00cd'), ('abcd', 3))

    def test_multilingual_text_reports_skips(self):
        self.assertEqual(prepare_vdi_text('é中→😀'), ('', 4))
