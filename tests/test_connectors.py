import unittest

from last30days_universal.connectors import search_hn, search_reddit


class TestConnectors(unittest.TestCase):
    def test_hn_mock_shape(self):
        payload = search_hn("quantum computing", mock=True, max_results=3)
        self.assertEqual(payload["status"], "mock-hn")
        results = payload["organicResults"]
        self.assertTrue(results)
        for r in results:
            self.assertIn("news.ycombinator.com", r["url"])
            self.assertIn("quantum computing", r["title"].lower() + r["snippet"].lower())

    def test_reddit_mock_shape(self):
        payload = search_reddit("quantum computing", mock=True, max_results=2)
        self.assertEqual(payload["status"], "mock-reddit")
        self.assertTrue(payload["organicResults"])
        for r in payload["organicResults"]:
            self.assertIn("reddit.com", r["displayedUrl"])

    def test_mock_is_deterministic(self):
        a = search_hn("same query", mock=True)
        b = search_hn("same query", mock=True)
        self.assertEqual(
            [r["url"] for r in a["organicResults"]],
            [r["url"] for r in b["organicResults"]],
        )


if __name__ == "__main__":
    unittest.main()
