---
name: comfy-shot-film
description: Coordinate still images and videos on the local ComfyUI. Use when the user asks Codex for a picture, an edit, or a short film. Codex selects and follows qwen-image-prompts, h3-prompt-writing, and comfy-h3-shots. The user does not choose skills. Deliver the image or video, not only a prompt. Do not invent a new workflow or rewrite those skills.
---

# 短片生成

用户只对 Codex 说要什么图、什么视频。Codex 按本技能协调，不让用户自己选技能或切换 agent。

- 静帧提示词用 `qwen-image-prompts`。
- 视频提示词、旁白和对白用 `h3-prompt-writing`。
- 提交到 `192.168.0.200:8188` 用 `comfy-h3-shots`。

用户要的是图或视频时，就提交并检查结果，不要停在提示词。一部片子用同一套图，不新做工作流。本技能决定分镜、用哪张图、先跑哪一镜、第一帧过不过。提示词仍按上面两个技能写。

## 提示词交给哪两个技能

静帧，包括角色、场景、道具和改图：先读已安装的 `$qwen-image-prompts`，再读该技能 `references/v10.md` 里对应的路线。调用名是 `$qwen-image-prompts`。透明底句子和本机参数才看 `references/templates.md`。普通素材保持短，不要擅自做成海报。

视频，包括 4 步参考图镜头、8 步接尾帧、旁白和对白：先读已安装的 `$h3-prompt-writing`。参考图镜头再读该技能 `references/ref-en.txt` 的六段。接上一镜尾帧再读该技能 `references/base-en.txt`。调用名是 `$h3-prompt-writing`。不要改段名，不要把中文写进画面描述。中文只放在 `<d>[Chinese] ...</d>` 里。旁白必须用那个技能里的 `says in an off-screen voiceover`，并写明嘴保持闭着。

5 秒里只放一句旁白，或一问一答两个短句。给用户看的中文意思写在镜头表，不放进提交文件。

## 怎么分镜

换动物或换场景，用 4 步 `--mode ref`。最多两张图：一张角色，一张场景。不要把上一镜尾帧传进去。个数和朝向必须画在角色图里。只写“五条、头朝右”而图里不是这样，第一帧会多一只或朝反。

只有动作接着拍，才用 8 步 `--mode fl`。第一张图必须是上一镜真正的最后一帧，不能是草图。4 步全部做完再做 8 步。

每镜默认 5 秒，1056×608，124 帧。提交用 `$comfy-h3-shots` 目录里的 `scripts/submit_shot.py`。透明底先铺到宣纸上再提交，否则紫底会进视频。

先看第一帧的个数、朝向、有没有跳成另一张图。不过就改参考图重出这一镜。过了再接下一步。8 步还要和上一镜尾帧比。

这台 5080 上，两张参考图的 4 步大约 80 秒。8 步因为要换模型，大约 128 秒。更早单图测试的 65 秒不要当成现在的默认。
