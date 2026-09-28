#!/usr/bin/env python3
"""Submit one MiniMax H3 shot to the local ComfyUI."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HOST = "http://192.168.0.200:8188"
REF_UNET = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
FL_UNET = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
REF_LORA = "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"
FL_LORA = "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"
CLIP = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VIDEO_VAE = "minimax_h3_video_vae_fp16.safetensors"
AUDIO_VAE = "minimax_h3_audio_vae_fp32.safetensors"


def frames(seconds: float) -> int:
    count = max(5, round(seconds * 24))
    return count + (5 - count % 17) % 17


def upload(host: str, path: Path) -> str:
    data = path.read_bytes()
    boundary = uuid.uuid4().hex
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            data,
            f"\r\n--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue',
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(
        host + "/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)["name"]


def graph(args, names: list[str], length: int) -> dict:
    turbo = not args.full
    steps = 20 if args.full else (4 if args.mode == "ref" else 8)
    unet = REF_UNET if args.mode == "ref" else FL_UNET
    model = ["1", 0]
    nodes = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VIDEO_VAE}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": AUDIO_VAE}},
    }
    if turbo:
        lora = REF_LORA if args.mode == "ref" else FL_LORA
        nodes["2"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": 1.0},
        }
        model = ["2", 0]
    cond = {
        "clip": ["3", 0],
        "vae": ["4", 0],
        "prompt": Path(args.prompt_file).read_text(),
        "width": args.width,
        "height": args.height,
        "length": length,
    }
    if args.mode == "ref":
        cond["audio_vae"] = ["5", 0]
        cond["ref_image_size"] = "match"
        for index, name in enumerate(names):
            nodes[str(20 + index)] = {"class_type": "LoadImage", "inputs": {"image": name}}
            cond[f"ref_images.ref_image_{index}"] = [str(20 + index), 0]
        nodes["7"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": cond}
    else:
        if names:
            nodes["20"] = {"class_type": "LoadImage", "inputs": {"image": names[0]}}
            cond["first_frame"] = ["20", 0]
        if len(names) > 1:
            nodes["21"] = {"class_type": "LoadImage", "inputs": {"image": names[1]}}
            cond["last_frame"] = ["21", 0]
        nodes["7"] = {"class_type": "MiniMaxH3ImageToVideo", "inputs": cond}
    nodes["8"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}}
    nodes["9"] = {
        "class_type": "BasicScheduler",
        "inputs": {"model": model, "scheduler": "simple", "steps": steps, "denoise": 1.0},
    }
    nodes["10"] = {"class_type": "BasicGuider", "inputs": {"model": model, "conditioning": ["7", 0]}}
    nodes["11"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": args.seed}}
    nodes["12"] = {
        "class_type": "SamplerCustomAdvanced",
        "inputs": {
            "noise": ["11", 0],
            "guider": ["10", 0],
            "sampler": ["8", 0],
            "sigmas": ["9", 0],
            "latent_image": ["7", 1],
        },
    }
    nodes["13"] = {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["4", 0]}}
    nodes["14"] = {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["12", 0], "vae": ["5", 0]}}
    nodes["15"] = {
        "class_type": "CreateVideo",
        "inputs": {"images": ["13", 0], "audio": ["14", 0], "fps": 24.0},
    }
    nodes["16"] = {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["15", 0],
            "filename_prefix": args.prefix,
            "format": "auto",
            "codec": "auto",
        },
    }
    return nodes


def submit(host: str, nodes: dict) -> str:
    payload = json.dumps({"prompt": nodes}).encode()
    req = urllib.request.Request(
        host + "/prompt", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)["prompt_id"]
    except urllib.error.HTTPError as exc:
        raise SystemExit(exc.read().decode()[:2000]) from exc


def wait(host: str, prompt_id: str) -> None:
    while True:
        with urllib.request.urlopen(host + "/history/" + prompt_id, timeout=30) as response:
            history = json.load(response)
        if prompt_id not in history:
            time.sleep(5)
            continue
        status = history[prompt_id]["status"]
        timestamps = {}
        for event in status.get("messages") or []:
            if isinstance(event, list) and event[0] in ("execution_start", "execution_success"):
                timestamps[event[0]] = event[1].get("timestamp")
        elapsed = ""
        if len(timestamps) == 2:
            elapsed = f" {(timestamps['execution_success'] - timestamps['execution_start']) / 1000:.1f}s"
        print(status.get("status_str"), prompt_id + elapsed, flush=True)
        print(json.dumps(history[prompt_id].get("outputs"), ensure_ascii=False), flush=True)
        if status.get("status_str") != "success":
            raise SystemExit(1)
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("ref", "fl"), required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--image", type=Path, action="append", default=[])
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--width", type=int, default=1056)
    parser.add_argument("--height", type=int, default=608)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--prefix", default="video/h3")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()
    if args.width % 32 or args.height % 32:
        raise SystemExit("width and height must be multiples of 32")
    if args.mode == "ref" and len(args.image) > 2:
        raise SystemExit("ref takes at most one character image and one scene image")
    if args.mode == "fl" and len(args.image) > 2:
        raise SystemExit("fl takes a first frame and an optional last frame")
    names = [upload(args.host, path) for path in args.image]
    length = frames(args.seconds)
    prompt_id = submit(args.host, graph(args, names, length))
    print(prompt_id, f"{args.width}x{args.height}", f"{length}f", flush=True)
    if not args.no_wait:
        wait(args.host, prompt_id)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        assert frames(5) == 124
        assert frames(15) == 362
        assert frames(0.1) == 5
        print("ok")
    else:
        main()
