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

### `qwen-plan-image`

通过千问 Token Plan API 生成图片并保存到本地，默认使用 `qwen-image-3.0-pro`，尺寸为 `576×1024`（9:16 竖屏）。支持个人版和团队版，包含凭证检查、结果下载、文件校验及错误处理。默认模型已完成个人版实际生图验证。

需要 `curl`、Python 3，以及对应套餐的 API Key。优先读取 `QWEN_PLAN_API_KEY`，也可使用已确认属于千问 Token Plan 的 `OPENAI_API_KEY`。不要将密钥写入技能或提交到仓库。

技能正文见 [`skills/qwen-plan-image/SKILL.md`](skills/qwen-plan-image/SKILL.md)。

### `omlx-tts`

通过本机 oMLX HTTP 接口生成中文语音回复或朗读音频，默认使用 `Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit` 和 `vivian` 音色，支持切换预设音色。

需要 macOS、Python 3，以及已运行并下载兼容模型的 oMLX。脚本仅使用 Python 标准库，从本机 oMLX 配置读取端口和密钥，不需要在技能中填写凭证。

- 日常语音使用 `--play`：调用 macOS 自带的 `afplay`，播放成功后自动清理临时音频。
- 明确需要保存时传入 `--output`，文件不会自动删除。
- 播放失败时保留音频供重试；不重新合成，不覆盖已有文件。
- 提供预设音色朗读，不提供声音克隆、语音识别或实时通话。

技能正文见 [`skills/omlx-tts/SKILL.md`](skills/omlx-tts/SKILL.md)。


### `comfy-shot-film`

Codex 的入口。用户只说要什么图或短片，不必自己选技能。它调用下面三个技能，提交到本机 ComfyUI，并检查成片。不停在提示词上，也不新做工作流。

### `qwen-image-prompts`

为 Qwen Image 2.1 写静帧提示词：角色、场景、道具、改图。按 V10 的文生图、参考创作、原图编辑三条路线。采样参数不写进提示词。

这不是 `qwen-plan-image`。那个技能走云端 Token Plan API；这个只写本机 Comfy 的提示词。

### `h3-prompt-writing`

为 MiniMax H3 写视频提示词、旁白和对白。参考图镜头用该技能的 `references/ref-en.txt`，接上一镜尾帧用 `references/base-en.txt`。中文只放在 `<d>[Chinese] ...</d>`。

### `comfy-h3-shots`

把写好的提示词提交到 ComfyUI。不负责写提示词。脚本是该技能目录里的 `scripts/submit_shot.py`，只用 Python 标准库。

四个技能一起装。关系是：

```text
comfy-shot-film
├── qwen-image-prompts    静帧提示词
├── h3-prompt-writing     视频、旁白、对白
└── comfy-h3-shots        提交到 ComfyUI
```

`qwen-image-prompts` 和 `h3-prompt-writing` 互不替代。只有 `comfy-h3-shots` 连接 ComfyUI。

环境：

- 提交机要能访问 ComfyUI。默认 `http://192.168.0.200:8188`，用 `--host` 改。
- 当前这台是 RTX 5080 16GB、内存 32GB。下面的耗时只对这台有效。
- Python 3.9 或更高版本。提交脚本不需要额外安装包。
- Qwen 本机权重：`qwen_image_2.1_int8_convrot.safetensors`，文本编码器 `qwen3vl_8b_int8_convrot.safetensors`（类型 `qwen_image`），VAE `qwen_image_2.1_vae_bf16.safetensors`。采样是 `euler` + `simple`，cfg 1，25 步，负面词留空。官方注释是 bf16、40 步，不要写进提示词。
- H3 权重：`minimax_h3_ref2va_pruned_int8_convrot.safetensors` 配 4 步 LoRA `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors`；`minimax_h3_fl2va_pruned_int8_convrot.safetensors` 配 8 步 LoRA `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`。
- 默认 1056×608、24fps、124 帧、5 秒。换角色或场景用 `--mode ref`，最多一张角色图加一张场景图。只有动作续拍用 `--mode fl`，第一张必须是上一镜真实尾帧。
- 这台 5080 上，两张参考图的 4 步大约 80 秒；换模型的 8 步大约 128 秒。
- 不使用 LTX-2.3 22B，除非单镜必须超过约 15 秒。
- 透明底 PNG 先铺到背景上再进视频，否则紫底会进去。


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

安装图片生成 Skill：

```bash
skills add sukris/agent-skills \
  --global \
  --skill qwen-plan-image \
  --agent claude-code codex \
  --yes
```

安装本机语音 Skill：

```bash
skills add sukris/agent-skills \
  --global \
  --skill omlx-tts \
  --agent claude-code codex \
  --yes
```

安装后可以说“用语音回答”或“读给我听”。也可直接运行：

```bash
python3 skills/omlx-tts/scripts/speak.py --play --text '你好，这是中文语音测试。'
```

运行无需模型或音频设备的测试：

```bash
python3 -m unittest discover -s skills/omlx-tts/scripts -p 'test_*.py'
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


安装 Comfy 短片技能（四个一起装）：

```bash
skills add sukris/agent-skills \
  --global \
  --skill comfy-shot-film qwen-image-prompts h3-prompt-writing comfy-h3-shots \
  --agent claude-code codex \
  --yes
```

装好后直接说要什么图或短片。手动提交时把 `<skill-dir>` 换成该技能目录：

```bash
python3 <skill-dir>/scripts/submit_shot.py --mode ref --prompt-file shot.txt --image char.png --image scene.png
python3 <skill-dir>/scripts/submit_shot.py --mode fl --prompt-file shot.txt --image tail.png
```

不连接服务器的帧数自检：

```bash
python3 skills/comfy-h3-shots/scripts/submit_shot.py
```

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
├── memos-memory/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── qwen-plan-image/
│   └── SKILL.md
├── omlx-tts/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── scripts/
│       ├── speak.py
│       └── test_speak.py
├── comfy-shot-film/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── qwen-image-prompts/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/
│       ├── v10.md
│       └── templates.md
├── h3-prompt-writing/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── references/
│       ├── ref-en.txt
│       └── base-en.txt
└── comfy-h3-shots/
    ├── SKILL.md
    ├── agents/openai.yaml
    └── scripts/submit_shot.py

mcp/
└── memos/
    ├── server.py
    └── tests/test_server.py
```

## 许可证

本仓库使用 [MIT License](LICENSE)。
