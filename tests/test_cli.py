import json
import tempfile
import unittest
from pathlib import Path

from last30days_universal.cli import build_parser, run


class TestCli(unittest.TestCase):
    def _run(self, extra=None):
        with tempfile.TemporaryDirectory() as tmp:
            argv = [
                "--topic", "electric vehicle batteries",
                "--entities", "Tesla,CATL",
                "--mock", "--query-limit", "5",
                "--output-dir", tmp,
                "--run-id", "test-run",
            ] + (extra or [])
            args = build_parser().parse_args(argv)
            out_dir = run(args)
            files = {p.name for p in Path(out_dir).iterdir()}
            data = {name: (Path(out_dir) / name).read_text() for name in files}
            return out_dir, files, data

    def test_full_artifact_set(self):
        _, files, data = self._run()
        expected = {
            "brief.md", "evidence.csv", "evidence.jsonl",
            "queries_used.json", "raw_serp_results.json", "run_metadata.json",
        }
        self.assertTrue(expected.issubset(files))
        # Brief is topic-general and carries evidence IDs.
        self.assertIn("electric vehicle batteries", data["brief.md"])
        self.assertIn("E001", data["brief.md"])
        # Metadata reflects the run.
        meta = json.loads(data["run_metadata.json"])
        self.assertEqual(meta["topic"], "electric vehicle batteries")
        self.assertEqual(meta["entities"], ["Tesla", "CATL"])
        self.assertGreater(meta["evidence_count"], 0)

    def test_extract_writes_pages(self):
        _, files, _ = self._run(extra=["--extract", "--extract-top", "3"])
        self.assertIn("extracted_pages.jsonl", files)

    def test_topic_is_required(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--mock"])


if __name__ == "__main__":
    unittest.main()
