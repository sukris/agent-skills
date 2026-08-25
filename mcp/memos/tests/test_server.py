import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "server.py"


def load_server():
    spec = importlib.util.spec_from_file_location("memos_mcp_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    defaults = {
        "MEMOS_BASE_URL": "http://127.0.0.1:8000",
        "MEMOS_DEFAULT_USER_ID": "default_user",
        "MEMOS_DEFAULT_CUBE_ID": "shared_memory",
        "MEMOS_DEFAULT_CUBE_NAME": "Shared Memory",
    }
    with patch.dict(os.environ, defaults):
        spec.loader.exec_module(module)
    return module


class MemosMcpUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def test_tool_annotations_distinguish_reads_and_writes(self):
        tools = {tool["name"]: tool for tool in self.server.TOOLS}
        self.assertTrue(tools["memory_search"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["memory_add"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["memory_add"]["annotations"]["idempotentHint"])

    def test_search_uses_default_identity_and_cube(self):
        with patch.object(
            self.server,
            "api_post",
            return_value={"code": 200, "data": {"results": []}},
        ) as api_post:
            result = self.server.call_tool("memory_search", {"query": "language preference"})

        api_post.assert_called_once_with(
            "/product/search",
            {
                "query": "language preference",
                "user_id": "default_user",
                "readable_cube_ids": ["shared_memory"],
                "top_k": 5,
            },
        )
        self.assertFalse(result["isError"])

    def test_add_ensures_cube_before_write(self):
        calls = []

        def fake_post(path, payload):
            calls.append((path, payload))
            if path == "/product/exist_mem_cube_id":
                return {"code": 200, "data": {"shared_memory": False}}
            if path == "/product/create_cube":
                return {"code": 200, "data": {"cube_id": "shared_memory"}}
            return {"code": 200, "data": {"memory_ids": ["m1"]}}

        with patch.object(self.server, "api_post", side_effect=fake_post):
            result = self.server.call_tool(
                "memory_add",
                {"content": "Use Simplified Chinese by default.", "source": "user_preference"},
            )

        self.assertEqual(
            [path for path, _ in calls],
            ["/product/exist_mem_cube_id", "/product/create_cube", "/product/add"],
        )
        add_payload = calls[-1][1]
        self.assertEqual(add_payload["user_id"], "default_user")
        self.assertEqual(add_payload["writable_cube_ids"], ["shared_memory"])
        self.assertEqual(add_payload["messages"][0]["content"], "Use Simplified Chinese by default.")
        self.assertTrue(result["structuredContent"]["stored"])

    def test_ensure_cube_treats_unique_conflict_as_existing(self):
        with patch.object(
            self.server,
            "api_post",
            side_effect=[
                {"code": 200, "data": {"shared_memory": False}},
                RuntimeError("MemOS HTTP 500: UNIQUE constraint failed: cubes.cube_id"),
            ],
        ):
            result = self.server.ensure_cube("shared_memory", "default_user", "Shared Memory")

        self.assertFalse(result["created"])
        self.assertEqual(result["cube_id"], "shared_memory")


class MemosMcpProtocolTests(unittest.TestCase):
    def test_stdio_initialize_and_tool_list(self):
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        proc = subprocess.run(
            [sys.executable, str(SERVER_PATH)],
            input="".join(json.dumps(item) + "\n" for item in requests),
            text=True,
            capture_output=True,
            env={**os.environ, "MEMOS_BASE_URL": "http://127.0.0.1:9"},
            timeout=10,
            check=True,
        )
        responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "memos-memory")
        tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
        self.assertEqual(tool_names, {"memory_ensure_cube", "memory_search", "memory_add", "memory_list"})


if __name__ == "__main__":
    unittest.main()
