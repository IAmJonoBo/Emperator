# Emperator CLI Reference

The `emperator` command line interface streamlines day-to-day maintenance tasks for both humans and AI copilots.

## Global options

- `--root PATH`: run commands against a different checkout (defaults to the current directory).
- `--telemetry-store {memory,jsonl,off}`: choose how the CLI persists analyzer telemetry (in-memory
  for ephemeral sessions, JSONL for on-disk history, or disabled).
- `--telemetry-path PATH`: override the default `.emperator/telemetry` directory when using the JSONL
  store.
- `--version`, `-v`: display the CLI version and exit.

## Scaffold commands

- `emperator scaffold audit`: print the expected directory structure and highlight missing TODO stubs.
- `emperator scaffold ensure [--dry-run]`: create any missing directories/files with TODO placeholders. Use `--dry-run` to preview the plan.

## Environment doctor

- `emperator doctor env [--apply]`: run workstation diagnostics (Python version, uv CLI, virtualenv, pnpm, helper scripts). Pass `--apply` to execute the recommended remediation actions sequentially.

## Contract validation

- `emperator contract validate [--strict]`: run structural checks against the canonical OpenAPI contract. The command reports
  missing metadata, malformed path definitions, and schema issues in the `/contract` response. Pass `--strict` to treat
  warnings (such as absent server entries) as errors.

## Auto-remediation helpers

- `emperator fix plan`: list the curated remediation commands (tooling bootstrap, lint hook refresh, JS tooling install).
- `emperator fix run [--only NAME] [--apply]`: execute one or more remediation actions. Without `--apply` the command operates in dry-run mode so you can review the plan first.

Outputs are rendered with Rich progress spinners and colour-coded tables for quick scanning.

## Analysis planning

- `emperator analysis inspect`: build an at-a-glance report that highlights detected languages, example files, and whether Semgrep, CodeQL, and the Tree-sitter CLI are installed. The command renders progress bars while collecting the data and concludes with actionable hints.
- `emperator analysis wizard`: guide developers (and copilots) through the steps required to bring the IR pipeline online, highlighting missing tooling with friendly reminders and celebrating ready-to-use analyzers.
- `emperator analysis plan`: synthesise an execution plan for supported analyzers, including the exact Semgrep and CodeQL commands to run and whether the tools are ready to execute.
  When telemetry persistence is enabled the command also surfaces the plan fingerprint, last run
  timestamp, and the on-disk telemetry directory (if applicable).
- `emperator analysis run [--tool NAME --severity LEVEL --include-unready]`: execute analyzer plans, stream per-command progress, and persist telemetry for every step.
  Use `--tool` multiple times to narrow execution to specific analyzers, `--severity` to focus on findings tagged as `info`, `low`, `medium`, `high`, or `critical`, and `--include-unready` to force tools that still report missing prerequisites.
  Severity filters are recorded in telemetry metadata and any analyzer step skipped by the filter is noted in the run summary for quick auditing.
  The CLI prints a summary table with success/failure indicators, the highest severity reported per tool, and a gating badge (`PASS`, `REVIEW`, or `BLOCK`) derived from the contract severity tiers. Medium findings require manual review, while high/critical findings trigger a blocking gate and are echoed in the run-level notes. The command also records the run fingerprint so you can compare results against cached telemetry.
