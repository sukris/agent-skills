---
name: "qwen-plan-image"
description: "通过千问 Token Plan 图片生成 API，根据文字描述生成图片并保存到本地。适用于用户要求文生图或明确指定 qwen-plan-image 的场景；不用于图片理解、语音或视频生成。"
---

# Token Plan 图片生成

根据用户提示词调用 Token Plan API，下载图片并交付本地文件链接。沿用对话中已确认的提示词和参数，不反复询问；保留用户指定的模型、风格、构图和内容，不擅自改写主题。

## 模型与参数

以下图片生成模型已列入官方 Token Plan 个人版及团队版模型清单；列入清单不代表当前凭证已有使用资格。默认使用 `qwen-image-3.0-pro`。

| 系列 | 模型 ID | 选择规则 |
| --- | --- | --- |
| 千问 | `qwen-image-3.0-pro` | 用户未指定时的默认模型 |
| 万相 | `wan2.7-image` | 用户指定时使用 |
| 万相 | `wan2.7-image-pro` | 用户指定时使用 |

- 默认生成一张，默认尺寸 `768*1024`（3:4 竖屏）。将用户输入的 `768×1024` 或 `768x1024` 规范为 `768*1024`；具体尺寸是否支持以所选模型官方文档或服务端响应为准。
- 多张图片、参考图编辑、负面提示词、seed 等参数仅在对应模型接口已有依据时传入，不猜测参数名称、范围或异步协议。当前请求示例仅覆盖文生图。
- 不按模型名称推断价格、速度或质量排序，不自动切换模型。若需要更新接口，以 Token Plan 官方文档为准，不直接套用其他平台同名模型的协议。

## 凭证与适用套餐

- 个人版与团队版均支持上表三个图片生成模型，使用用户实际订阅对应的 Token Plan API Key。官方 Codex 页的生图示例虽写团队版，但不能据此排除个人版；套餐支持范围应以对应套餐当前模型清单为准。个人版、团队版、按量计费的 Key 不互通，不混用。官方示例环境变量名为 `OPENAI_API_KEY`。
- 个人版官方说明允许在编程或智能体工具中，通过 Skill 等扩展交互式发起模型调用；本技能按用户请求执行属于此场景，不将其扩展为无人值守批量任务或应用后端。
- `QWEN_PLAN_API_KEY` 是本技能沿用的自定义专用变量，不是官方必需变量。已配置时优先使用；否则使用已确认属于千问 Token Plan 的 `OPENAI_API_KEY`。两者都存在时不要依次试用不同密钥。
- `OPENAI_API_KEY` 也可能存放其他供应商的凭证；使用前依据用户已确认的配置或已知来源确定用途，不把不明来源的凭证发送到千问接口，不在回复中显示凭证。
- 环境变量检查和 API 提交在同一次 shell 调用内进行。当前工具进程未继承变量，只能说明该进程不可用，不能断言用户本机没有配置；若前后检查结果不一致，先排查启动环境。桌面进程不会必然继承另一个终端临时设置的变量，不擅自修改全局配置或读取无关凭证文件。

## 执行流程

1. 确认提示词、模型、尺寸与保存目录；检查 `curl`、用于 JSON 序列化和解析的工具（如 Python 3）及上述凭证来源。缺少密钥时请用户在当前运行环境配置，不要求在聊天中发送密钥，不搜索无关文件寻找凭证。
2. 在保存目录下创建唯一任务子目录，例如 `mktemp -d "$PWD/qwen-image-XXXXXX"`；未指定保存目录时使用当前工作目录。将实际参数序列化为其中的 `request.json`，避免直接把任意提示词拼入 shell 命令或手写 JSON。
3. 提交一次请求，将响应保存为同目录下的 `response.json`，记录 HTTP 状态及返回的 `request_id`；按下述错误规则判定结果，不仅检查命令是否结束。
4. 提取响应中的图片 URL 并逐张下载到任务目录。下载失败时保留成功的图片与响应文件，只重试下载，不重新提交生成请求。
5. 核验实际文件并交付绝对路径链接；多图任务列出成功数量及失败项。只清理本次产生的下载残片，不删除成功图片、已有文件或其他任务的数据。

用户指定目录不可写时按环境权限机制处理，不悄悄改为其他最终保存位置。

## 请求示例

在唯一任务目录内执行，先用 JSON 序列化工具将实际参数写入 `request.json`。下面展示请求结构，不是需要原样提交的提示词：

```json
{
  "model": "qwen-image-3.0-pro",
  "input": {
    "messages": [
      {
        "role": "user",
        "content": [{"text": "用户的图片描述"}]
      }
    ]
  },
  "parameters": {
    "size": "768*1024",
    "n": 1,
    "watermark": false,
    "prompt_extend": false,
    "enable_thinking": false
  }
}
```

以下地址、请求结构与图片响应路径与官方 Codex 生图示例一致；该页面示例默认模型为 `qwen-image-2.0`。`qwen-image-3.0-pro` 已使用个人版凭证完成实际生图和下载验证；两个万相模型仅完成官方清单核对，尚未实测。上述附加参数按 `qwen-image-3.0-pro` 的本次成功请求记录，不据此推断其他模型参数兼容。此处使用生图原生接口，不要替换为聊天用的 `/compatible-mode/v1`。

```bash
# 仅在确认 OPENAI_API_KEY 属于千问 Token Plan 后使用该回退。
qwen_image_key="${QWEN_PLAN_API_KEY:-${OPENAI_API_KEY:-}}"
: "${qwen_image_key:?当前进程缺少千问 Token Plan API Key}"
curl --silent --show-error --fail-with-body \
  --connect-timeout 15 --max-time 180 \
  -X POST 'https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer ${qwen_image_key}" \
  -H 'Content-Type: application/json' \
  --data-binary @request.json \
  -o response.json \
  --write-out '%{http_code}\n'
```

不要开启 shell tracing 或输出 Authorization 头。调试信息仅保留必要的 HTTP 状态、错误码、错误说明与请求 ID；不在回复中公开完整签名图片 URL 或密钥。

## 响应与下载

- 检查 HTTP 状态和 JSON 响应内容。图片 URL 位于 `output.choices[].message.content[].image`，兼容项目实现中的 `url` 字段；content 为单个对象时先转为列表，再遍历全部 choices 与 content，忽略非图片项，对重复 URL 去重。
- 非 JSON 响应、错误结构或无图片 URL 都不能作为生成成功的证据。若只有任务 ID，按所选模型的官方异步协议查询；没有协议依据时报告任务 ID 和“已提交，尚未取得图片”，不要猜测轮询地址或再次提交。
- 下载使用独立请求，不携带 Token Plan API Key。只接受 HTTP(S) 图片 URL；不要把返回的任意字符串作为命令执行。
- 使用 `curl --location --fail --show-error --connect-timeout 15 --max-time 120` 下载，并以 `--proto '=http,https' --proto-redir '=http,https'` 限制协议。先写入唯一的 `.part` 文件，避免留下看似完整的失败产物。
- 下载完成后检查退出码、文件非空，并用 `file --mime-type` 或文件签名确认是图片，拒绝 HTML/JSON 错误页。按实际格式选择扩展名，再将 `.part` 改名为最终文件；不要仅凭 URL 后缀认定格式。
- 默认无需读取图片进行视觉评估；文件类型检查不等于内容或画质验证。用户要求检查画面时，再使用可用的图片查看能力。

## 错误与重试

| 情况 | 处理 |
| --- | --- |
| 缺少凭证、401 或认证错误 | 停止请求，检查当前进程是否继承变量、Key 所属套餐、订阅状态及密钥完整性，不回显密钥 |
| `403 AccessDenied.Unpurchased` | 服务端拒绝当前凭证访问该模型；核对请求中的模型 ID、Key 所属套餐及订阅状态，不仅凭此错误断言整个套餐不支持生图或要求升级团队版 |
| 其他 403 | 按返回错误说明报告，不一律解释为未购买 |
| 模型、尺寸或参数错误 | 按文档或明确报错修正；涉及用户已指定的参数变更时说明并确认 |
| 内容审核拒绝 | 如实说明服务端拒绝，不声称所有平台都禁止，也不自动反复改词重试 |
| 429、5xx、提交超时或连接中断 | 报告失败或结果未知；不自动重发生成 POST，避免重复生成和计费；有任务 ID 时优先按官方协议查状态 |
| 图片下载失败 | 生成与保存分开报告；现有 URL 可用时最多重试下载两次，仍失败则保留响应并说明原因 |

`qwen-image-2.0` 未列入当前个人版清单；单个模型的权限失败不能用于推断整个套餐不支持生图。不要将 HTTP 200、工具无输出或请求已发出等同于成功生成。

## 交付

成功时简短报告实际模型与保存结果，附 `[查看图片](/绝对路径/图片.png)`；可用图片预览时直接展示本地图片。只有已取得图片并完成文件核验，才称“已生成并保存”。

失败时报告已完成的阶段、错误码或原因、是否已取得图片、是否已保存，以及继续所需条件。不得虚构路径、画质验证或安全拦截。

## 官方依据

- [Codex 接入与图像生成 Skill 示例](https://platform.qianwenai.com/docs/developer-guides/clients-and-developer-tools/codex)：`OPENAI_API_KEY`、生图接口、请求与响应结构；其中示例对套餐的表述需与对应套餐最新清单交叉核对。
- [Token Plan 个人版概览](https://platform.qianwenai.com/docs/token-plan/personal/token-plan-personal-overview)：个人版图片模型清单及工具内交互式 Skill 调用范围。
- [Token Plan 团队版概览](https://platform.qianwenai.com/docs/token-plan/team/token-plan-team-overview)：当前支持的模型清单。

文档核对日期：2026-09-16。

## 实测记录

2026-09-16：使用个人版凭证和当时的 `1024*1024` 参数调用 `qwen-image-3.0-pro`，返回 HTTP 200，成功下载并验证一张 1024×1024 PNG。验证覆盖该模型和参数组合；两个万相模型尚未实测。

默认尺寸现已调整为 `768*1024`（3:4 竖屏）；该尺寸尚未进行实际 API 验证。
