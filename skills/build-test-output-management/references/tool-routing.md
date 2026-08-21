# Tool Routing

Use this reference only when selecting a build, compile, lint, or test command.

## Decision order

1. Narrow the scope to the smallest target that can verify the current change.
2. Prefer a dedicated RTK adapter for compact exploratory output.
3. Use `rtk test`, `rtk err`, or `rtk summary` for unsupported tools when a raw log is not required.
4. Use the capture helper when the command may be noisy or evidence must remain available.
5. Use focused raw output only when the compact evidence cannot identify the cause.
6. Use the capture helper or a native report for final pass/fail evidence; do not rely on an RTK wrapper's outer exit status.

## Node.js and TypeScript

| Purpose | Preferred command shape |
|---|---|
| npm script | `rtk npm run <script>` |
| TypeScript | `rtk tsc --noEmit` |
| Jest | `rtk jest <test-path-or-pattern>` |
| Vitest | `rtk vitest run <test-path-or-pattern>` |
| Next.js build | `rtk next build` |
| ESLint | `rtk lint <paths>` |
| Playwright | `rtk playwright test <test-path>` |
| Unsupported runner | `rtk test <command>` |

Prefer one workspace, package, test file, or test name over a repository-wide run. Preserve JSON, JUnit, coverage, trace, and screenshot artifacts outside the conversation; inspect only failures and relevant deltas.

## Java

| Purpose | Preferred command shape |
|---|---|
| Maven module tests | `rtk mvn -pl <module> -am test` |
| Maven test class/method | `rtk mvn -Dtest=<Class>#<method> test` |
| Maven verification | `rtk mvn verify` |
| Gradle module tests | `rtk gradlew :<module>:test` |
| Gradle test class/method | `rtk gradlew :<module>:test --tests <pattern>` |
| Unsupported Java command | `rtk err <command>` |

Prefer Maven Surefire/Failsafe XML under `target/` and Gradle XML/HTML reports under `build/` over raw console output. Read the failing testcase, assertion, and deepest relevant cause; do not load successful testcase logs.

## Generic fallback

| Need | Command |
|---|---|
| Failures only | `rtk test <command>` |
| Errors and warnings | `rtk err <command>` |
| Heuristic overview | `rtk summary <command>` |
| Full raw output for a narrowed command | `rtk proxy <command>`; inspect output, not the wrapper status |

For long-running or high-volume commands, prefer the capture helper over terminal output so the raw evidence remains available without entering model context.
