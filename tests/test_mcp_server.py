import unittest

from last30days_universal.mcp_server import handle_message


class TestMcpServer(unittest.TestCase):
    def test_initialize(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "last30days-universal")

    def test_tools_list(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertIn("run_report", names)

    def test_tools_call_run_report_mock(self):
        resp = handle_message({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "run_report", "arguments": {"topic": "note apps", "mock": True, "query_limit": 3}},
        })
        self.assertFalse(resp["result"]["isError"])
        self.assertIn("Research Brief", resp["result"]["content"][0]["text"])

    def test_unknown_tool_is_error(self):
        resp = handle_message({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        })
        self.assertIn("error", resp)

    def test_initialized_notification_returns_none(self):
        self.assertIsNone(handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))


if __name__ == "__main__":
    unittest.main()
