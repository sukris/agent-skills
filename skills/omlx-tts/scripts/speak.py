#!/usr/bin/env python3
"""Generate a validated WAV using the user's local oMLX HTTP service."""
import argparse
import http.client
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import shutil
import time
import wave

MODEL = "Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit"


def speak(text, output, settings_path, voice="vivian", model=MODEL, language="Chinese"):
    if not text.strip():
        raise ValueError("朗读文本不能为空")
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"输出已存在，请换一个文件名：{output}")
    settings = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    port = int(settings.get("server", {}).get("port", 8000))
    if not 1 <= port <= 65535:
        raise ValueError("oMLX 端口无效")
    key = settings.get("auth", {}).get("api_key")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps({"model": model, "input": text, "voice": voice,
                       "language": language, "response_format": "wav"}).encode("utf-8")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=300)
    started = time.monotonic()
    try:
        connection.request("POST", "/v1/audio/speech", body, headers)
        response = connection.getresponse()
        if response.status != 200:
            detail = response.read(2000).decode("utf-8", errors="replace")
            if key:
                detail = detail.replace(key, "[REDACTED]")
            raise RuntimeError(f"oMLX HTTP {response.status}: {detail}")
        data = response.read()
    finally:
        connection.close()
    with wave.open(io.BytesIO(data), "rb") as audio:
        frames, rate = audio.getnframes(), audio.getframerate()
        if frames <= 0 or rate <= 0:
            raise ValueError("oMLX 返回了空音频")
        if len(audio.readframes(frames)) != frames * audio.getnchannels() * audio.getsampwidth():
            raise ValueError("oMLX 返回的 WAV 数据不完整")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as file:
        file.write(data)
    return {"path": str(output), "model": model, "voice": voice,
            "duration_seconds": round(frames / rate, 2), "sample_rate": rate,
            "elapsed_seconds": round(time.monotonic() - started, 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", help="省略时从标准输入读取 UTF-8 文本")
    parser.add_argument("--output", help="显式保存音频；--play 时省略则使用临时文件，播放成功后删除")
    parser.add_argument("--voice", default="vivian")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--play", action="store_true", help="生成后通过 macOS afplay 播放并等待结束")
    args = parser.parse_args()
    if not args.output and not args.play:
        parser.error("仅生成文件时需要 --output；临时播放请使用 --play")
    temporary_dir = tempfile.mkdtemp(prefix="omlx-tts-") if not args.output else None
    output = args.output or str(Path(temporary_dir) / "speech.wav")
    base = Path(os.environ.get("OMLX_BASE_PATH") or Path.home() / ".omlx")
    try:
        result = speak(args.text if args.text is not None else sys.stdin.read(),
                       output, base / "settings.json", args.voice, args.model, args.language)
    except (OSError, ValueError, RuntimeError, http.client.HTTPException, wave.Error, EOFError) as exc:
        print(f"语音生成失败：{exc}", file=sys.stderr)
        if temporary_dir:
            shutil.rmtree(temporary_dir)
        return 1
    result["temporary"] = temporary_dir is not None
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.play:
        try:
            subprocess.run(["/usr/bin/afplay", result["path"]], check=True,
                           timeout=max(30, result["duration_seconds"] + 15))
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"音频已保存，但播放失败：{exc}", file=sys.stderr)
            return 1
        if temporary_dir:
            shutil.rmtree(temporary_dir)
        print(json.dumps({"playback_completed": True, "deleted": temporary_dir is not None}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
