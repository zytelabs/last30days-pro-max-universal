import unittest

from last30days_universal.query_pack import build_query_pack, quote_phrase, slugify


class TestQueryPack(unittest.TestCase):
    def test_bare_topic_comes_first(self):
        queries = build_query_pack("electric vehicles")
        self.assertEqual(queries[0], '"electric vehicles"')

    def test_single_word_topic_not_quoted(self):
        queries = build_query_pack("kubernetes")
        self.assertEqual(queries[0], "kubernetes")

    def test_recency_and_intent_modifiers_present(self):
        queries = build_query_pack("electric vehicles")
        joined = " || ".join(queries)
        self.assertIn('"electric vehicles" latest', joined)
        self.assertIn('"electric vehicles" alternatives', joined)

    def test_entities_expand_into_queries(self):
        queries = build_query_pack("note apps", entities=["Obsidian", "Notion"])
        joined = " || ".join(queries)
        self.assertIn("Obsidian review", joined)
        self.assertIn("Obsidian vs Notion", joined)

    def test_sites_become_site_filters(self):
        queries = build_query_pack("rust async", sites=["github.com", "https://reddit.com/"])
        joined = " || ".join(queries)
        self.assertIn("site:github.com", joined)
        self.assertIn("site:reddit.com", joined)

    def test_dedup_and_cap(self):
        queries = build_query_pack("ai", entities=["ai", "ai"], max_queries=5)
        self.assertLessEqual(len(queries), 5)
        self.assertEqual(len(queries), len(set(q.lower() for q in queries)))

    def test_year_hint(self):
        queries = build_query_pack("world cup", year="2026")
        self.assertIn('"world cup" 2026', queries)

    def test_quote_phrase_and_slug(self):
        self.assertEqual(quote_phrase("two words"), '"two words"')
        self.assertEqual(quote_phrase("solo"), "solo")
        self.assertEqual(slugify("Hello, World!"), "hello-world")


if __name__ == "__main__":
    unittest.main()
