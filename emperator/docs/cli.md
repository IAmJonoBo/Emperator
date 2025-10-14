# Emperator CLI Reference

The `emperator` command line interface streamlines day-to-day maintenance tasks for both humans and AI copilots.

## Global options

- `--root PATH`: run commands against a different checkout (defaults to the current directory).

## Scaffold commands

- `emperator scaffold audit`: print the expected directory structure and highlight missing TODO stubs.
- `emperator scaffold ensure [--dry-run]`: create any missing directories/files with TODO placeholders. Use `--dry-run` to preview the plan.

## Environment doctor

- `emperator doctor env [--apply]`: run workstation diagnostics (Python version, virtualenv, pnpm, helper scripts). Pass `--apply` to execute the recommended remediation actions sequentially.

## Auto-remediation helpers

- `emperator fix plan`: list the curated remediation commands (tooling bootstrap, lint hook refresh, JS tooling install).
- `emperator fix run [--only NAME] [--apply]`: execute one or more remediation actions. Without `--apply` the command operates in dry-run mode so you can review the plan first.

Outputs are rendered with Rich progress spinners and colour-coded tables for quick scanning.
