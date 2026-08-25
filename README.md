# Agent Skills

这是我维护的 Agent Skills 集合，可通过 [`skills`](https://skills.sh/) CLI 安装到 Claude Code、Codex 等兼容 Agent。

## 可用技能

### `memos-memory`

通过仓库内的 MemOS MCP 适配器，为 Codex、Claude Code、OpenCode 等 Agent 提供共享长期记忆。Skill 负责何时读取和写入记忆，MCP 适配器负责调用 MemOS REST API。

代码位置：

- `skills/memos-memory/`
- `mcp/memos/`

### `build-test-output-management`

管理高噪声的构建、编译、lint 和测试输出：完整执行证据保存在对话之外，只把退出码、耗时、测试汇总、关键诊断和日志位置返回给 Agent。

适用场景包括：

- Maven、Gradle、Vite、TypeScript、Jest、Vitest 等可能产生大量日志的命令；
- 需要保留完整 stdout/stderr 以便后续复查；
- 需要避免把数千行正常构建输出塞入模型上下文；
- 需要依据目标命令的真实退出码，而不是外层包装命令状态进行判断。

## 安装

列出仓库中的技能：

```bash
skills add sukris/agent-skills --list
```

全局安装到 Claude Code：

```bash
skills add sukris/agent-skills \
  --global \
  --skill build-test-output-management \
  --agent claude-code \
  --yes
```

同时安装到 Claude Code 和 Codex：

```bash
skills add sukris/agent-skills \
  --global \
  --skill build-test-output-management \
  --agent claude-code codex \
  --yes
```

安装长期记忆 Skill：

```bash
skills add sukris/agent-skills \
  --global \
  --skill memos-memory \
  --agent claude-code codex \
  --yes
```

Skill 还需要在对应 Agent 中配置仓库内的 `mcp/memos/server.py`。环境变量和 stdio 配置示例见 [`mcp/memos/README.md`](mcp/memos/README.md)。

`skills` CLI 通常会把全局技能源放在 `~/.agents/skills/`，并为所选 Agent 创建相应安装入口。实际路径和链接关系以当前 CLI 版本的输出为准。

## 使用要求

- Python 3.9 或更高版本；
- 可执行目标构建或测试命令所需的本地工具；
- 使用技能建议的 RTK 路由时，需要安装 [`rtk`](https://github.com/rtk-ai/rtk)。捕获脚本本身只依赖 Python 标准库。

技能中的捕获助手可直接运行：

```bash
python3 skills/build-test-output-management/scripts/capture_command.py \
  -- npm test
```

它会：

1. 在私有临时目录中保存完整的 `full.log`；
2. 生成机器可读的 `summary.json`；
3. 输出有界的关键证据摘要；
4. 返回目标命令的真实退出码。

## 安全与日志处理

> [!WARNING]
> `full.log` 保存目标命令未经全面脱敏的原始 stdout/stderr，可能包含 token、密码、环境变量、私有仓库 URL、内部主机名、客户数据或业务堆栈信息。

- 摘要和命令展示会对常见凭据格式做尽力脱敏，但这不代表 `full.log` 已脱敏；
- 不要把 `full.log` 提交到 Git、公开上传为 CI artifact、粘贴到 Issue，或未经检查直接分享；
- 默认临时目录权限为 `0700`，`full.log` 与 `summary.json` 权限为 `0600`；
- 如使用 `--log-dir`，请确保目标目录位于仓库之外、不被同步软件自动上传且访问受控；
- `.gitignore` 只能防止未跟踪日志被误提交，不能保护已经加入 Git 索引的敏感文件。

## 仓库结构

```text
skills/
├── build-test-output-management/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/tool-routing.md
│   └── scripts/capture_command.py
└── memos-memory/
    ├── SKILL.md
    └── agents/openai.yaml

mcp/
└── memos/
    ├── server.py
    └── tests/test_server.py
```

## 许可证

本仓库使用 [MIT License](LICENSE)。
