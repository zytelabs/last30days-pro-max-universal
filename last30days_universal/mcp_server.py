"""Minimal MCP server exposing the listening pipeline as agent-callable tools.

Implements the Model Context Protocol over stdio using JSON-RPC 2.0 with the
stdlib only (no MCP SDK dependency). Handles ``initialize``, ``tools/list``,
and ``tools/call`` against the tool registry in
:mod:`last30days_universal.tools`.

Run it as the program an MCP client launches:

    python3 -m last30days_universal.mcp_server
"""

from __future__ import annotations

import json
import sys

from . import __version__
from .tools import TOOLS

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "last30days-universal", "version": __version__}

_TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def _result(message_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _tool_descriptors() -> list[dict]:
    return [
        {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
        for t in TOOLS
    ]


def _call_tool(params: dict, message_id) -> dict:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    tool = _TOOLS_BY_NAME.get(name)
    if tool is None:
        return _error(message_id, -32602, f"Unknown tool: {name}")
    try:
        result = tool["handler"](arguments)
    except Exception as exc:  # noqa: BLE001 - report tool failures to the client, don't crash
        return _result(message_id, {
            "content": [{"type": "text", "text": f"Error: {type(exc).__name__}: {exc}"}],
            "isError": True,
        })
    return _result(message_id, {
        "content": [{"type": "text", "text": json.dumps(result)}],
        "isError": False,
    })


def handle_message(message: dict):
    """Handle one JSON-RPC message; return a response dict, or None for notifications."""
    method = message.get("method")
    message_id = message.get("id")

    if method == "initialize":
        return _result(message_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(message_id, {"tools": _tool_descriptors()})
    if method == "tools/call":
        return _call_tool(message.get("params") or {}, message_id)

    if message_id is None:
        return None
    return _error(message_id, -32601, f"Method not found: {method}")


def serve(stdin=None, stdout=None) -> None:
    """Read JSON-RPC messages line-by-line from stdin and write responses to stdout."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "Parse error")) + "\n")
            stdout.flush()
            continue
        response = handle_message(message)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()


def main(argv: list[str] | None = None) -> int:
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
