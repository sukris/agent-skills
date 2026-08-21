#!/usr/bin/env python3
"""Run a command, preserve its complete output, and print a bounded evidence summary."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
from typing import Any, Optional


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CRITICAL_RE = re.compile(
    r"\b(error|exception|failed|failure|fatal|caused by|assertionerror|"
    r"compilation failure|build failed|test failed|tests failed)\b|"
    r"\b[A-Za-z_$][A-Za-z0-9_.$]*(?:Error|Exception)\b",
    re.IGNORECASE,
)
SUMMARY_RE = re.compile(
    r"^ran\s+\d+\s+tests?\s+in|^ok$|"
    r"\b(tests? run|test suites?|tests?:|passed:|failed:|failures?:|errors?:|"
    r"skipped:|build success|build failed|compilation failure)\b",
    re.IGNORECASE,
)
LOCATION_RE = re.compile(
    r"(?:^|\s)(?:at\s+)?[^:\s]+\."
    r"(?:java|kt|kts|js|jsx|ts|tsx|mjs|cjs|py|go|rs|cs|php|rb):"
    r"\d+(?::\d+)?",
    re.IGNORECASE,
)
ZERO_FAILURE_RE = re.compile(
    r"\b0\s+(errors?|failures?|failed tests?|failed)\b", re.IGNORECASE
)
BEARER_RE = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(
    r"\b(api[_-]?key|access[_-]?token|token|password|passwd|secret|authorization)"
    r"(\s*[:=]\s*)([^\s,;]+)",
    re.IGNORECASE,
)
SECRET_FLAG_RE = re.compile(
    r"(--(?:api[-_]?key|access[-_]?token|token|password|passwd|secret)=)([^\s]+)",
    re.IGNORECASE,
)
SECRET_FLAGS = {
    "--api-key",
    "--api_key",
    "--access-token",
    "--access_token",
    "--token",
    "--password",
    "--passwd",
    "--secret",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture full command output and emit a compact evidence summary."
    )
    parser.add_argument("--cwd", help="Working directory for the target command.")
    parser.add_argument("--log-dir", help="Fresh directory for full.log and summary.json.")
    parser.add_argument("--label", default="build-test", help="Label stored in summary.json.")
    parser.add_argument(
        "--max-key-lines",
        type=int,
        default=24,
        help="Maximum line-numbered evidence entries printed and stored.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    if args.max_key_lines < 4:
        parser.error("--max-key-lines must be at least 4")
    return args


def redact_text(text: str) -> str:
    redacted = BEARER_RE.sub("Bearer [REDACTED]", text)
    redacted = SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", redacted)
    return SECRET_FLAG_RE.sub(r"\1[REDACTED]", redacted)


def redact_command(arguments: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for argument in arguments:
        if redact_next:
            redacted.append("[REDACTED]")
            redact_next = False
            continue
        redacted.append(redact_text(argument))
        if argument.lower() in SECRET_FLAGS:
            redact_next = True
    return redacted


def clean_excerpt(line: str, limit: int = 500) -> str:
    cleaned = redact_text(ANSI_RE.sub("", line).rstrip("\r\n"))
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def create_log_dir(requested: Optional[str]) -> Path:
    if requested:
        path = Path(requested).expanduser().resolve()
        path.mkdir(parents=True, mode=0o700, exist_ok=False)
        path.chmod(0o700)
        return path
    path = Path(tempfile.mkdtemp(prefix="codex-build-test-"))
    path.chmod(0o700)
    return path


def select_key_lines(
    first: list[dict[str, Any]],
    last: collections.deque[dict[str, Any]],
    summaries: collections.deque[dict[str, Any]],
    maximum: int,
) -> list[dict[str, Any]]:
    by_line: dict[int, dict[str, Any]] = {}
    for item in [*first, *last, *summaries]:
        by_line[item["line"]] = item
    ordered = [by_line[number] for number in sorted(by_line)]
    if len(ordered) <= maximum:
        return ordered
    head = maximum // 2
    return ordered[:head] + ordered[-(maximum - head) :]


def main() -> int:
    args = parse_args()
    cwd = Path(args.cwd).expanduser().resolve() if args.cwd else Path.cwd().resolve()
    log_dir = create_log_dir(args.log_dir)
    full_log = log_dir / "full.log"
    summary_file = log_dir / "summary.json"
    redacted_command = redact_command(args.command)
    command_text = shlex.join(redacted_command)
    started_at = dt.datetime.now(dt.timezone.utc)
    started = time.monotonic()

    first_limit = args.max_key_lines // 2
    last_limit = args.max_key_lines - first_limit
    first_critical: list[dict[str, Any]] = []
    last_critical: collections.deque[dict[str, Any]] = collections.deque(
        maxlen=last_limit
    )
    summaries: collections.deque[dict[str, Any]] = collections.deque(maxlen=12)
    total_lines = 0
    critical_count = 0
    interrupted = False

    try:
        process = subprocess.Popen(
            args.command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError as error:
        full_log.write_text(f"{error}\n", encoding="utf-8")
        full_log.chmod(0o600)
        return_code = 127
    else:
        assert process.stdout is not None
        try:
            with full_log.open("w", encoding="utf-8") as output:
                for total_lines, line in enumerate(process.stdout, start=1):
                    output.write(line)
                    excerpt = clean_excerpt(line)
                    if not excerpt:
                        continue
                    is_summary = bool(SUMMARY_RE.search(excerpt))
                    is_location = bool(LOCATION_RE.search(excerpt))
                    is_critical = bool(CRITICAL_RE.search(excerpt)) and not bool(
                        ZERO_FAILURE_RE.search(excerpt)
                    )
                    item = {
                        "line": total_lines,
                        "kind": (
                            "critical"
                            if is_critical
                            else "location"
                            if is_location
                            else "summary"
                        ),
                        "text": excerpt,
                    }
                    if is_critical:
                        critical_count += 1
                        if len(first_critical) < first_limit:
                            first_critical.append(item)
                        else:
                            last_critical.append(item)
                    elif is_summary or is_location:
                        summaries.append(item)
            return_code = process.wait()
        except KeyboardInterrupt:
            interrupted = True
            process.terminate()
            try:
                return_code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                return_code = process.wait()
            return_code = 130

    full_log.chmod(0o600)

    duration = round(time.monotonic() - started, 3)
    finished_at = dt.datetime.now(dt.timezone.utc)
    key_lines = select_key_lines(
        first_critical, last_critical, summaries, args.max_key_lines
    )
    result = {
        "label": redact_text(args.label),
        "command": redacted_command,
        "command_text": command_text,
        "cwd": str(cwd),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": duration,
        "exit_code": return_code,
        "interrupted": interrupted,
        "total_output_lines": total_lines,
        "critical_line_count": critical_count,
        "full_log": str(full_log),
        "key_lines": key_lines,
    }
    summary_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary_file.chmod(0o600)

    status = "PASS" if return_code == 0 else "FAIL"
    print(f"status: {status}")
    print(f"exit_code: {return_code}")
    print(f"duration_seconds: {duration}")
    print(f"output_lines: {total_lines}")
    print(f"critical_lines: {critical_count}")
    print(f"full_log: {full_log}")
    print(f"summary_json: {summary_file}")
    if key_lines:
        print("evidence:")
        for item in key_lines:
            print(f"- L{item['line']} [{item['kind']}]: {item['text']}")
    else:
        print("evidence: none matched; inspect full_log if the exit code is non-zero")
    return return_code


if __name__ == "__main__":
    sys.exit(main())
