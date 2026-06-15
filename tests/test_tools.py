import unittest

from last30days_universal.tools import (
    TOOLS,
    tool_build_query_pack,
    tool_generate_report,
    tool_normalize_evidence,
    tool_run_report,
    tool_search_serp,
)


class TestTools(unittest.TestCase):
    def test_build_query_pack(self):
        out = tool_build_query_pack({"topic": "note apps", "entities": ["Obsidian"]})
        self.assertGreater(out["count"], 0)
        self.assertEqual(out["count"], len(out["queries"]))

    def test_search_serp_mock(self):
        out = tool_search_serp({"query": "note apps", "mock": True})
        self.assertTrue(out["organicResults"])

    def test_normalize_evidence(self):
        raws = [{"rank": 1, "title": "Obsidian", "url": "https://obsidian.md", "snippet": "x"}]
        out = tool_normalize_evidence({"raw_results": raws, "topic": "note apps", "entities": ["Obsidian"]})
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["evidence"][0]["entity"], "Obsidian")

    def test_run_report_mock_end_to_end(self):
        out = tool_run_report({"topic": "note apps", "entities": ["Obsidian"], "mock": True, "query_limit": 4})
        self.assertIn("Research Brief", out["report_markdown"])
        self.assertGreater(out["evidence_count"], 0)
        self.assertTrue(out["queries_used"])

    def test_generate_report(self):
        ev = tool_run_report({"topic": "note apps", "mock": True, "query_limit": 2})["evidence"]
        out = tool_generate_report({"topic": "note apps", "evidence": ev})
        self.assertIn("Research Brief", out["report_markdown"])

    def test_registry_well_formed(self):
        names = {t["name"] for t in TOOLS}
        self.assertEqual(names, {"build_query_pack", "search_serp", "normalize_evidence", "generate_report", "run_report"})
        for t in TOOLS:
            self.assertIn("inputSchema", t)
            self.assertTrue(callable(t["handler"]))


if __name__ == "__main__":
    unittest.main()
