import unittest

from last30days_universal.entities import detect_entity, entity_for_host, entity_slug


class TestEntities(unittest.TestCase):
    def test_no_entities_returns_none(self):
        self.assertEqual(detect_entity("t", "u", "s", "q", []), "None")

    def test_host_ownership_wins(self):
        got = detect_entity(
            title="Some unrelated headline",
            url="https://blog.obsidian.md/release",
            snippet="",
            query="note apps",
            names=["Notion", "Obsidian"],
        )
        self.assertEqual(got, "Obsidian")

    def test_title_mention_outranks_snippet_mention(self):
        got = detect_entity(
            title="Notion ships a new feature",
            url="https://example.com/x",
            snippet="this also mentions Obsidian briefly",
            query="note apps",
            names=["Obsidian", "Notion"],
        )
        self.assertEqual(got, "Notion")

    def test_unmatched_returns_none(self):
        got = detect_entity("nothing here", "https://example.com", "", "topic", ["Zyte"])
        self.assertEqual(got, "None")

    def test_entity_slug_and_host(self):
        self.assertEqual(entity_slug("Bright Data"), "brightdata")
        self.assertEqual(entity_for_host("docs.notion.so", ["Notion"]), "Notion")
        self.assertIsNone(entity_for_host("example.com", ["Notion"]))


if __name__ == "__main__":
    unittest.main()
