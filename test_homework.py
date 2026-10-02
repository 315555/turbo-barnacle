"""在临时目录验证会改变文件的功能，不接触真实作业。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import homework


class HomeworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "2026001_张三_高数作业.pdf").write_bytes(b"original")
        (self.root / "2026002_李四_英语作业.docx").write_bytes(b"second")
        (self.root / "notes.txt").write_bytes(b"leave alone")

    def tearDown(self):
        self.temp.cleanup()

    def test_scan_filters_extension(self):
        with patch("builtins.print") as output:
            homework.scan(self.root, "pdf")
        printed = "\n".join(str(call) for call in output.call_args_list)
        self.assertIn("高数作业.pdf", printed)
        self.assertNotIn("英语作业.docx", printed)

    def test_rename_requires_confirmation_and_undo_restores_bytes(self):
        with patch("builtins.input", return_value="n"):
            homework.rename(self.root)
        self.assertTrue((self.root / "2026001_张三_高数作业.pdf").exists())
        with patch("builtins.input", return_value="y"):
            homework.rename(self.root)
        self.assertEqual((self.root / "高数作业_2026001.pdf").read_bytes(), b"original")
        with patch("builtins.input", return_value="y"):
            homework.undo(self.root)
        self.assertEqual((self.root / "2026001_张三_高数作业.pdf").read_bytes(), b"original")

    def test_conflict_never_overwrites(self):
        (self.root / "高数作业_2026001.pdf").write_bytes(b"existing")
        with patch("builtins.input", return_value="y"):
            homework.rename(self.root)
        self.assertEqual((self.root / "高数作业_2026001.pdf").read_bytes(), b"existing")
        self.assertEqual((self.root / "2026001_张三_高数作业.pdf").read_bytes(), b"original")

    def test_archive_report_and_undo(self):
        conflict = self.root / "2026秋/pdf/2026001_张三_高数作业.pdf"
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b"do not overwrite")
        with patch("builtins.input", return_value="y"):
            homework.archive(self.root, "2026秋")
        self.assertEqual(conflict.read_bytes(), b"do not overwrite")
        self.assertEqual((self.root / "2026秋/docx/2026002_李四_英语作业.docx").read_bytes(), b"second")
        self.assertEqual((self.root / "2026秋/txt/notes.txt").read_bytes(), b"leave alone")
        report = next((self.root / ".homework_manager/reports").glob("*.txt"))
        self.assertIn("跳过：1 个", report.read_text(encoding="utf-8"))
        with patch("builtins.input", return_value="y"):
            homework.undo(self.root)
        self.assertEqual((self.root / "2026001_张三_高数作业.pdf").read_bytes(), b"original")
        self.assertEqual((self.root / "notes.txt").read_bytes(), b"leave alone")
        self.assertTrue(report.exists())


if __name__ == "__main__":
    unittest.main()
