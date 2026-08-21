---
name: build-test-output-management
description: Manage noisy build, compile, lint, and test output without losing evidence. Use when Node.js, Java, or other development commands may emit large logs that would flood the model context; skip it for commands whose complete output is already short and clear.
---

# Build/Test Output Management

Preserve complete execution evidence outside the conversation while returning only the information needed to decide the next action.

## Choose the execution mode

Use the least expensive mode that preserves enough evidence:

1. **Compact mode:** Use a dedicated RTK command for quick exploration when output is expected to be manageable and RTK supports the tool. Do not treat the RTK wrapper's process status as final validation evidence.
2. **Capture mode:** Use `scripts/capture_command.py` when output may be large, the command is unfamiliar, or a complete raw log is required for later inspection.
3. **Focused raw mode:** Use `rtk proxy` only after narrowing the command to a failing module, test, file, or task. Do not replay an entire noisy command without a new diagnostic reason.

Read [references/tool-routing.md](references/tool-routing.md) when choosing commands for Node.js, Java, tests, or generic tools.

## Before execution

- Identify the exact command, working directory, success condition, and expected report files.
- Narrow scope first: prefer one module, test class, test file, target, or package over the full repository.
- Do not enable verbose, debug, stacktrace, dependency, or environment dumps on the first run.

## Capture mode

Resolve the helper relative to this skill directory, then run:

```bash
rtk proxy <skill-dir>/scripts/capture_command.py -- <command> [args...]
```

The helper:

- stores the complete combined stdout/stderr in a unique private temporary directory;
- writes a machine-readable `summary.json`;
- prints a bounded summary with the target exit code, duration, log path, and line-numbered evidence;
- exits with the target command's exit code.

RTK versions may normalize the outer wrapper status. When invoking the helper through `rtk proxy`, use the helper's printed `exit_code` and `summary.json`, not the shell status of `rtk`, as the authoritative result.

Treat the raw log as the source of truth. A compact summary is an index into that evidence, not a replacement for it.

## Interpret the result

A successful-looking line is not sufficient. Verify the target exit code recorded by the capture helper and any required test/build report. Never infer pass/fail from the outer RTK wrapper status.

On failure, extract only:

- the failing stage, module, target, test class, or test name;
- the first actionable diagnostic with file and line when available;
- the deepest relevant `Caused by` or assertion difference;
- failure, error, skipped, and passed counts when the runner reports them;
- paths to the full log and structured reports.

If this is insufficient, inspect the cited line ranges in `full.log`, then rerun only the failing scope with higher verbosity. Never respond to missing evidence by dumping the complete log into the conversation.

## Native reports

Prefer structured reports over console text when they exist:

- JUnit XML, Maven Surefire/Failsafe reports, and Gradle test result files;
- Jest/Vitest JSON or JUnit output;
- ESLint/SARIF/JSON diagnostics;
- Playwright traces, screenshots, videos, and reports retained on failure.

Read only failed cases and their surrounding evidence. Do not load successful case details unless they affect the diagnosis.

## Required completion report

Report:

- command and working directory;
- exit code and duration;
- passed/failed/skipped counts when available;
- failed targets or tests and the most relevant root cause;
- full log/report paths;
- checks not executed, failed, or skipped.

Do not claim success when the target exit code, required reports, or acceptance criteria are unavailable. Use capture mode for final validation when the RTK adapter does not expose the target exit code reliably.

## Boundaries

- Keep generated logs outside the repository unless the user requests a project artifact.
- Do not delete logs needed for the current diagnosis.
- Do not expose secrets found in logs; cite their location and redact the value.
- Avoid repeated full builds when an incremental, module-scoped, or test-scoped command can answer the question.
