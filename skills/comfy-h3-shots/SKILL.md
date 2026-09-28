---
name: comfy-h3-shots
description: Plan and submit long-form MiniMax H3 shots on the local ComfyUI at 192.168.0.200:8188. Use when splitting a long video into shots, choosing ref2va or fl2va, or running a generation on this machine. Do not use for prompt wording; that belongs to h3-prompt-writing.
---

# Comfy H3 shots

One graph, many shots. Do not build a new workflow per film. Write the prompt with `h3-prompt-writing`, then submit it here.

Server: `http://192.168.0.200:8188`. RTX 5080 16GB, 32GB RAM. Daily weights are the installed MiniMax H3 int8 models. Leave LTX-2.3 22B alone unless one continuous shot must exceed H3's trained ~15 seconds.

## Which mode

- New scene or new character: `--mode ref`. Pass the character image and the scene image. Do not pass the previous shot's last frame.
- Same shot, motion continues: `--mode fl`. The image is that shot's last frame. A second image is the end pose.
- At most those two images. Reference sizing stays `match`.

Finish the `ref` shots before the `fl` shots. Switching UNETs reloads weights.

## Timed defaults

`ref`, turbo 4-step, 1056×608, 124 frames, one image, `res_multistep`, `simple`, no CFG:

- cold 77.3s, warm 65.4s
- file was 1056×608, 24fps, 124 frames, with audio

`fl` turbo is 8-step on `minimax_h3_fl2va`, same resolution and length, mug as the first frame: 126.8s. That run also loaded the other UNET, so it is not a warm fl-to-fl time.

Use `--full` (no turbo LoRA, 20 steps) only after a shot fails. The stock template says `beta` or `normal` can beat `simple` for reference-heavy 20-step prompts; that was not retested.

Frame count is `max(5, round(seconds * 24))` snapped onto `17k+5`. Trained range is 124–362. Default is 5 seconds. Do not go to 1344×768 unless 1056×608 failed.

## Submit

```bash
python3 <skill-dir>/scripts/submit_shot.py --mode ref --prompt-file shot.txt --image char.png --image scene.png
python3 <skill-dir>/scripts/submit_shot.py --mode fl --prompt-file shot.txt --image tail.png
```

The UI workflow `多参考图生成视频.json` is the same `ref` graph with the 4-step switch off. Use the script.
