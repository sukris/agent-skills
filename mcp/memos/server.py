#!/usr/bin/env python3
"""Dependency-free stdio MCP adapter for the MemOS REST API."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


SERVER_NAME = "memos-memory"
SERVER_VERSION = "1.0.0"
BASE_URL = os.getenv("MEMOS_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_USER_ID = os.getenv("MEMOS_DEFAULT_USER_ID", "default_user")
DEFAULT_CUBE_ID = os.getenv("MEMOS_DEFAULT_CUBE_ID", "shared_memory")
DEFAULT_CUBE_NAME = os.getenv("MEMOS_DEFAULT_CUBE_NAME", "Shared Memory")
HTTP_TIMEOUT = float(os.getenv("MEMOS_HTTP_TIMEOUT", "60"))


INSTRUCTIONS = (
    "Use memory_search before tasks where prior user preferences, project decisions, or recurring facts may matter. "
    "Use memory_add when the user explicitly asks to remember something or states a durable preference/decision. "
    "Do not store passwords, API keys, tokens, private keys, transient debugging output, or speculative conclusions. "
    f"Unless the user specifies otherwise, use user_id={DEFAULT_USER_ID!r} and cube_id={DEFAULT_CUBE_ID!r}."
)


TOOLS: list[dict[str, Any]] = [
    {
        "name": "memory_ensure_cube",
        "description": "Create the default MemOS memory cube if it does not already exist.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cube_id": {"type": "string", "description": "Stable memory cube ID."},
                "cube_name": {"type": "string", "description": "Human-readable cube name."},
                "owner_id": {"type": "string", "description": "Owner/user ID."},
            },
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Ensure MemOS cube",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "memory_search",
        "description": "Search long-term MemOS memories relevant to a query.",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "user_id": {"type": "string"},
                "cube_ids": {"type": "array", "items": {"type": "string"}},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
            },
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Search MemOS memory",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "memory_add",
        "description": "Store a durable user preference, project fact, decision, or lesson in MemOS.",
        "inputSchema": {
            "type": "object",
            "required": ["content"],
            "properties": {
                "content": {"type": "string", "minLength": 1},
                "source": {"type": "string", "description": "Short provenance label."},
                "user_id": {"type": "string"},
                "cube_id": {"type": "string"},
                "session_id": {"type": "string"},
                "async_mode": {"type": "string", "enum": ["sync", "async"], "default": "sync"},
            },
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Add MemOS memory",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
    {
        "name": "memory_list",
        "description": "List memories in a MemOS cube for inspection or auditing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "cube_id": {"type": "string"},
                "page": {"type": "integer", "minimum": 1, "default": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
            "additionalProperties": False,
        },
        "annotations": {
            "title": "List MemOS memories",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
]


def _validate_base_url() -> None:
    parsed = urllib.parse.urlparse(BASE_URL)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("MEMOS_BASE_URL must be an absolute HTTP(S) URL")


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    _validate_base_url()
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"MemOS HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"MemOS connection failed: {error.reason}") from error


def ensure_cube(cube_id: str, owner_id: str, cube_name: str) -> dict[str, Any]:
    exists = api_post("/product/exist_mem_cube_id", {"mem_cube_id": cube_id})
    if bool((exists.get("data") or {}).get(cube_id)):
        return {"cube_id": cube_id, "created": False, "response": exists}
    try:
        created = api_post(
            "/product/create_cube",
            {"cube_name": cube_name, "owner_id": owner_id, "cube_id": cube_id},
        )
    except RuntimeError as error:
        # Some MemOS versions may report false above while the user database
        # already contains the cube. Only this unique-key conflict is safe to
        # treat as idempotent success; other creation failures remain visible.
        if "UNIQUE constraint failed: cubes.cube_id" not in str(error):
            raise
        return {
            "cube_id": cube_id,
            "created": False,
            "response": {"code": 200, "message": "Cube already exists in user metadata"},
        }
    return {"cube_id": cube_id, "created": True, "response": created}


def _success(data: dict[str, Any], summary: str | None = None) -> dict[str, Any]:
    text = summary or json.dumps(data, ensure_ascii=False, indent=2)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": data,
        "isError": False,
    }


def _failure(error: Exception) -> dict[str, Any]:
    message = str(error)
    return {
        "content": [{"type": "text", "text": message}],
        "structuredContent": {"error": message},
        "isError": True,
    }


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    args = arguments or {}
    try:
        if name == "memory_ensure_cube":
            cube_id = args.get("cube_id") or DEFAULT_CUBE_ID
            owner_id = args.get("owner_id") or DEFAULT_USER_ID
            cube_name = args.get("cube_name") or DEFAULT_CUBE_NAME
            result = ensure_cube(cube_id, owner_id, cube_name)
            return _success(result, f"Memory cube {cube_id!r} ready; created={result['created']}.")

        if name == "memory_search":
            query = str(args.get("query") or "").strip()
            if not query:
                raise ValueError("query is required")
            payload = {
                "query": query,
                "user_id": args.get("user_id") or DEFAULT_USER_ID,
                "readable_cube_ids": args.get("cube_ids") or [DEFAULT_CUBE_ID],
                "top_k": int(args.get("top_k") or 5),
            }
            result = api_post("/product/search", payload)
            return _success(result)

        if name == "memory_add":
            content = str(args.get("content") or "").strip()
            if not content:
                raise ValueError("content is required")
            user_id = args.get("user_id") or DEFAULT_USER_ID
            cube_id = args.get("cube_id") or DEFAULT_CUBE_ID
            ensure_cube(cube_id, user_id, DEFAULT_CUBE_NAME)
            info: dict[str, Any] = {"source_type": args.get("source") or "agent_mcp"}
            payload: dict[str, Any] = {
                "user_id": user_id,
                "writable_cube_ids": [cube_id],
                "messages": [{"role": "user", "content": content}],
                "async_mode": args.get("async_mode") or "sync",
                "info": info,
            }
            if args.get("session_id"):
                payload["session_id"] = args["session_id"]
            response = api_post("/product/add", payload)
            result = {"stored": True, "cube_id": cube_id, "response": response}
            return _success(result, f"Stored durable memory in cube {cube_id!r}.")

        if name == "memory_list":
            payload = {
                "mem_cube_id": args.get("cube_id") or DEFAULT_CUBE_ID,
                "user_id": args.get("user_id") or DEFAULT_USER_ID,
                "page": int(args.get("page") or 1),
                "page_size": int(args.get("page_size") or 20),
            }
            result = api_post("/product/get_memory", payload)
            return _success(result)

        raise ValueError(f"unknown tool: {name}")
    except Exception as error:
        return _failure(error)


def _write(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized" or request_id is None:
        return None
    if method == "initialize":
        requested_version = (request.get("params") or {}).get("protocolVersion")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": requested_version or "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": call_tool(params.get("name", ""), params.get("arguments") or {}),
        }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for raw_line in sys.stdin:
        if not raw_line.strip():
            continue
        try:
            request = json.loads(raw_line)
            response = handle(request)
            if response is not None:
                _write(response)
        except Exception as error:
            _write(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(error)},
                }
            )


if __name__ == "__main__":
    main()
