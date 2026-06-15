import unittest

from last30days_universal.store import compute_deltas, connect, save_run


class TestStore(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def _ev(self, url, rank, title="t"):
        return {"evidence_id": "E1", "url": url, "query": "q", "title": title,
                "snippet": "s", "entity": "None", "source_type": "web", "serp_rank": rank}

    def test_baseline_run_has_no_previous(self):
        deltas = compute_deltas(self.conn, run_id="r1", topic="t", evidence=[self._ev("u1", 1)])
        self.assertIsNone(deltas["previous_run_id"])
        save_run(self.conn, run_id="r1", topic="t", created_at="2026-06-01", days=30, evidence=[self._ev("u1", 1)])

    def test_deltas_new_recurring_fading_rankchange(self):
        save_run(self.conn, run_id="r1", topic="t", created_at="2026-06-01", days=30,
                 evidence=[self._ev("u1", 1), self._ev("u2", 2)])
        current = [self._ev("u1", 3), self._ev("u3", 1)]  # u1 rank-changed, u2 fading, u3 new
        deltas = compute_deltas(self.conn, run_id="r2", topic="t", evidence=current)
        self.assertEqual(deltas["previous_run_id"], "r1")
        self.assertEqual([i["url"] for i in deltas["new"]], ["u3"])
        self.assertEqual([i["url"] for i in deltas["recurring"]], ["u1"])
        self.assertEqual([i["url"] for i in deltas["fading"]], ["u2"])
        self.assertEqual(deltas["rank_changed"][0]["old_rank"], 1)
        self.assertEqual(deltas["rank_changed"][0]["new_rank"], 3)

    def test_topic_isolation(self):
        save_run(self.conn, run_id="a1", topic="alpha", created_at="2026-06-01", days=30, evidence=[self._ev("u1", 1)])
        deltas = compute_deltas(self.conn, run_id="b1", topic="beta", evidence=[self._ev("u9", 1)])
        self.assertIsNone(deltas["previous_run_id"])


if __name__ == "__main__":
    unittest.main()
