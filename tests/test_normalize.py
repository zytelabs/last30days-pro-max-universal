import unittest

from last30days_universal.normalize import (
    assign_evidence_ids,
    classify_source_type,
    infer_signal_type,
    infer_theme_tags,
    normalize_serp_result,
)


class TestNormalize(unittest.TestCase):
    def test_source_classification(self):
        self.assertEqual(classify_source_type("https://www.reddit.com/r/x/1"), "community-reddit")
        self.assertEqual(classify_source_type("https://news.ycombinator.com/item?id=1"), "community-hn")
        self.assertEqual(classify_source_type("https://github.com/a/b"), "code-github")
        self.assertEqual(classify_source_type("https://docs.example.org/x"), "docs")
        self.assertEqual(classify_source_type("https://example.com/page"), "web")

    def test_signal_types(self):
        self.assertEqual(infer_signal_type("blog", "Introducing our new release"), "release")
        self.assertEqual(infer_signal_type("web", "X vs Y comparison"), "comparison")
        self.assertEqual(infer_signal_type("web", "how to do the thing"), "how-to")
        self.assertEqual(infer_signal_type("community-reddit", "this is broken and blocked"), "pain-point")
        self.assertEqual(infer_signal_type("community-reddit", "general chat"), "discussion")

    def test_theme_tags_skip_stopwords(self):
        tags = infer_theme_tags("the best guide to kubernetes operators", "kubernetes")
        self.assertIn("kubernetes", tags)
        self.assertNotIn("the", tags)
        self.assertNotIn("best", tags)

    def test_normalize_shape_and_ids(self):
        raw = {"rank": 1, "title": "Obsidian release notes", "url": "https://obsidian.md/r", "snippet": "new stuff"}
        item = normalize_serp_result(raw, "note apps", "2026-06-15T00:00:00Z", "note apps", ["Obsidian"])
        self.assertEqual(item["entity"], "Obsidian")
        self.assertEqual(item["signal_type"], "release")
        self.assertIn("theme_tags", item)
        self.assertTrue(item["why_it_matters"])
        self.assertTrue(item["recommended_action"])
        assign_evidence_ids([item])
        self.assertEqual(item["evidence_id"], "E001")


if __name__ == "__main__":
    unittest.main()
