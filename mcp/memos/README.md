# MemOS MCP Adapter

这是一个仅依赖 Python 标准库的 stdio MCP 适配器，将 Agent 的 MCP 调用转发到 MemOS REST API。

## 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MEMOS_BASE_URL` | `http://127.0.0.1:8000` | MemOS REST API 地址 |
| `MEMOS_DEFAULT_USER_ID` | `default_user` | 默认记忆用户 |
| `MEMOS_DEFAULT_CUBE_ID` | `shared_memory` | 默认共享记忆 Cube |
| `MEMOS_DEFAULT_CUBE_NAME` | `Shared Memory` | 默认 Cube 名称 |
| `MEMOS_HTTP_TIMEOUT` | `60` | HTTP 超时秒数 |

在 MCP 客户端中以 stdio 方式启动：

```json
{
  "mcpServers": {
    "memos": {
      "command": "python3",
      "args": ["/path/to/agent-skills/mcp/memos/server.py"],
      "env": {
        "MEMOS_BASE_URL": "http://your-memos-host:8000",
        "MEMOS_DEFAULT_USER_ID": "your-user-id",
        "MEMOS_DEFAULT_CUBE_ID": "shared_memory"
      }
    }
  }
}
```

提供 `memory_ensure_cube`、`memory_search`、`memory_add` 和 `memory_list` 四个工具。适配器不提供删除工具，也不会存储任何凭据。

## 测试

```bash
python3 -m unittest discover -s mcp/memos/tests -v
```
