#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { accessSync, constants } from "node:fs";
import path from "node:path";
import process from "node:process";

const args = process.argv.slice(2).filter((arg) => arg !== "--");
const { error: logError, log: logInfo } = globalThis.console;

const SUPPORTED_FLAGS = new Set(["--all", "--check"]);
const wantsAll = args.includes("--all");
const wantsCheck = args.includes("--check");
const unsupportedArgs = args.filter((arg) => !SUPPORTED_FLAGS.has(arg));

if (unsupportedArgs.length > 0) {
  logError(`Unknown format option(s): ${unsupportedArgs.join(", ")}`);
  process.exit(1);
}

if (wantsAll && wantsCheck) {
  logError("--all cannot be combined with --check");
  process.exit(1);
}

const runCommand = (command, commandArgs, options = {}) => {
  const result = spawnSync(command, commandArgs, {
    stdio: "inherit",
    env: process.env,
    ...options,
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

const npmExec = process.env.npm_execpath ?? "pnpm";

const runScript = (scriptName, scriptArgs = [], options = {}) => {
  runCommand(npmExec, ["run", scriptName, ...scriptArgs], options);
};

const resolveUv = () => {
  const candidates = [
    process.env.UV_BIN,
    process.env.UV,
    process.env.UV_PATH,
    path.join(process.env.HOME ?? "", ".cargo", "bin", "uv"),
    "uv",
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      if (candidate.includes(path.sep)) {
        accessSync(candidate, constants.X_OK);
        return candidate;
      }

      const probe = spawnSync(candidate, ["--version"], {
        stdio: "ignore",
      });
      if (probe.status === 0) {
        return candidate;
      }
    } catch (error) {
      const code = error?.code ?? "";
      if (code !== "ENOENT" && code !== "EACCES") {
        throw error;
      }
    }
  }

  return null;
};

const tasks = [];

const yamlArgs = wantsCheck ? ["--", "--check"] : [];
tasks.push(() => runScript("fmt:yaml", yamlArgs));

if (wantsCheck) {
  tasks.push(() =>
    runCommand(npmExec, [
      "exec",
      "biome",
      "check",
      "--formatter-enabled=true",
      "--linter-enabled=false",
      ".",
    ])
  );
} else {
  tasks.push(() => runScript("fmt:biome"));
}

const uvBinary = resolveUv();
if (!uvBinary) {
  logError(
    "pnpm fmt requires uv on PATH (or UV_BIN) so Ruff can format and sort imports. Install uv from https://docs.astral.sh/uv/ and retry."
  );
  process.exit(1);
}

tasks.push(() =>
  runCommand(uvBinary, ["run", "ruff", "format", ...(wantsCheck ? ["--check"] : []), "."])
);

const importArgs = ["run", "ruff", "check", ".", "--select", "I"];
tasks.push(() => runCommand(uvBinary, wantsCheck ? importArgs : [...importArgs, "--fix"]));

if (wantsAll) {
  tasks.push(() => runCommand(uvBinary, ["run", "ruff", "check", ".", "--fix"]));
}

for (const task of tasks) {
  task();
}

logInfo(wantsCheck ? "Formatting check complete" : "Formatting complete");
