---
name: qwen-image-prompts
description: Write Qwen Image 2.1 still-image prompts with the V10 A/B/C routes. Text-to-image stays observational English. Reference creation and edits follow the user's language and only change what was authorized. Use when a still prompt needs Qwen logic, a completed design direction, or beautification inside the allowed area. Character cutouts still use the RGBA template. Do not use for MiniMax H3 video prompts or for writing sampler settings into the prompt.
---

# Qwen Image 2.1 提示词

只负责静帧提示词。视频提示词用 `h3-prompt-writing`。

先读 `references/v10.md`，只读当前任务那一条路线。透明底句子和本机参数在 `references/templates.md`，不要把步数、尺寸写进提示词。

## 交给用户和交给模型的不一样

先用中文给用户看三行：固定要求、参考图各自继承什么、这次补上的画面决定。用户没要设计感时，最后一行写“不额外美化”。

提交给 Qwen 的只有提示词正文。不要附分析、标题、路线名或参数。

## 三条路线

- 没有要继承的图：文生图。英文，现在时，像在看一张已经存在的画。普通角色、道具、场景保持短。海报、封面、广告才补设计。
- 用图的一部分做新画面：参考创作。按用户语言写。开头说明每张图用什么、不用什么。两张及以上才写 `<image1>`、`<image2>`，按输入顺序。
- 改原图：只写要改的对象、范围和结果，加上必须保留的部分。不把局部修改写成一张新海报。

角色和道具要透明底时，用 `templates.md` 的本机句子把描述包起来，存 PNG。场景和海报不要套这句。
