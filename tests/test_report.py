import unittest

from last30days_universal.normalize import assign_evidence_ids, normalize_serp_result
from last30days_universal.report import SECTION_INDEX, build_indexed_report


def _evidence():
    raws = [
        {"rank": 1, "title": "Obsidian release notes", "url": "https://obsidian.md/r", "snippet": "introducing new sync"},
        {"rank": 2, "title": "Notion vs Obsidian", "url": "https://example.com/cmp", "snippet": "comparison of note apps"},
        {"rank": 3, "title": "Reddit: my notes are broken", "url": "https://www.reddit.com/r/x/1", "snippet": "this is broken"},
    ]
    items = [normalize_serp_result(r, "note apps", "2026-06-15T00:00:00Z", "note apps", ["Obsidian", "Notion"]) for r in raws]
    return assign_evidence_ids(items)


class TestReport(unittest.TestCase):
    def test_report_has_topic_title_and_all_sections(self):
        report = build_indexed_report(
            topic="note apps",
            entities=["Obsidian", "Notion"],
            angles=["sync"],
            evidence=_evidence(),
            date_range="2026-05-16 → 2026-06-15",
            run_id="test-run",
        )
        self.assertIn('"note apps" Research Brief', report)
        for section in SECTION_INDEX:
            self.assertIn(section, report)

    def test_evidence_ids_referenced(self):
        report = build_indexed_report(
            topic="note apps",
            entities=["Obsidian"],
            angles=[],
            evidence=_evidence(),
            date_range="r",
            run_id="test-run",
        )
        self.assertIn("E001", report)
        self.assertIn("E003", report)

    def test_empty_evidence_still_renders(self):
        report = build_indexed_report(
            topic="anything",
            entities=[],
            angles=[],
            evidence=[],
            date_range="r",
            run_id="empty",
        )
        self.assertIn("Research Brief", report)
        self.assertIn("No entities were tracked", report)

    def test_deltas_section(self):
        deltas = {
            "previous_run_id": "prev",
            "previous_created_at": "2026-06-01",
            "new": [{"evidence_id": "E001", "title": "X", "entity": "Obsidian"}],
            "recurring": [],
            "fading": [{"title": "old", "serp_rank": 4}],
            "rank_changed": [{"title": "moved", "old_rank": 3, "new_rank": 1}],
        }
        report = build_indexed_report(
            topic="note apps", entities=[], angles=[], evidence=_evidence(),
            date_range="r", run_id="test-run", deltas=deltas,
        )
        self.assertIn("Compared against previous run `prev`", report)
        self.assertIn("rank 3 → 1", report)


if __name__ == "__main__":
    unittest.main()
