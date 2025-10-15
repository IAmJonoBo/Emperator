#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { accessSync, constants, existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const { error: logError, log: logInfo, warn: logWarn } = globalThis.console;

const usage = `Usage: lint-changed.mjs [OPTIONS]

Run Ruff, Biome, and ESLint against changed files to speed up local feedback.

Options:
  --files <path>    Explicit file to lint (repeatable).
  --since <ref>     Compare against a Git ref (diff-filter=ACMR).
  --staged          Only inspect staged changes (default when no --files/--since).
  --fix             Apply available autofixes (Ruff --fix, Biome --write, ESLint --fix).
  -h, --help        Show this help message.`;

const rawArgs = process.argv.slice(2);
const options = {
  files: [],
  since: undefined,
  staged: false,
  fix: false,
};

for (let index = 0; index < rawArgs.length; index += 1) {
  const arg = rawArgs[index];
  switch (arg) {
    case "--files": {
      if (index + 1 >= rawArgs.length) {
        logError("Expected a path after --files.");
        process.exit(1);
      }
      const value = rawArgs[index + 1];
      index += 1;
      const segments = value
        .split(",")
        .map((segment) => segment.trim())
        .filter(Boolean);
      if (segments.length === 0) {
        logError("No paths provided to --files.");
        process.exit(1);
      }
      options.files.push(...segments);
      break;
    }
    case "--since": {
      if (index + 1 >= rawArgs.length) {
        logError("Expected a revision after --since.");
        process.exit(1);
      }
      options.since = rawArgs[index + 1];
      index += 1;
      break;
    }
    case "--staged": {
      options.staged = true;
      break;
    }
    case "--fix": {
      options.fix = true;
      break;
    }
    case "-h":
    case "--help": {
      logInfo(usage);
      process.exit(0);
      break;
    }
    default: {
      if (arg.startsWith("-")) {
        logError(`Unknown option: ${arg}`);
        process.exit(1);
      }
      logError(`Unexpected positional argument: ${arg}`);
      process.exit(1);
    }
  }
}

if (options.files.length > 0 && options.since) {
  logError("Cannot combine --files with --since.");
  process.exit(1);
}

if (options.files.length > 0 && options.staged) {
  logError("Cannot combine --files with --staged.");
  process.exit(1);
}

const repoRoot = process.cwd();

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
      const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" });
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

const uvBinary = resolveUv();
if (!uvBinary) {
  logError("uv is required to run Ruff. Install uv and ensure it is on PATH.");
  process.exit(1);
}

const npmExec = process.env.npm_execpath ?? "pnpm";

const collectGitFiles = () => {
  if (options.files.length > 0) {
    return options.files;
  }

  const git = (gitArgs) => {
    const result = spawnSync("git", gitArgs, {
      cwd: repoRoot,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
      encoding: "utf8",
    });

    if (typeof result.status === "number" && result.status !== 0) {
      const stderr = result.stderr?.trim();
      logError(`git ${gitArgs.join(" ")} failed${stderr ? `: ${stderr}` : ""}`);
      process.exit(1);
    }

    const output = result.stdout ?? "";
    return output
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  };

  if (options.since) {
    return git(["diff", "--name-only", "--diff-filter=ACMR", `${options.since}...HEAD`]);
  }

  const stagedFiles = git(["diff", "--name-only", "--diff-filter=ACMR", "--cached"]);
  const workingTreeFiles = git(["diff", "--name-only", "--diff-filter=ACMR"]);
  const combined = new Set([...stagedFiles, ...workingTreeFiles]);
  return Array.from(combined);
};

const candidateFiles = collectGitFiles();
if (candidateFiles.length === 0) {
  logInfo("[lint-changed] No files to lint.");
  process.exit(0);
}

const pythonFiles = [];
const biomeFiles = [];
const eslintFiles = [];

const biomeMatchers = [
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".mjs",
  ".cjs",
  ".json",
  ".jsonc",
  ".css",
  ".scss",
  ".html",
  ".yml",
  ".yaml",
  ".md",
  ".mdx",
];

const eslintMatchers = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"];

for (const file of candidateFiles) {
  const absolute = path.join(repoRoot, file);
  if (!existsSync(absolute)) {
    logWarn(`[lint-changed] Skipping missing file: ${file}`);
    continue;
  }

  const ext = path.extname(file).toLowerCase();
  if (ext === ".py") {
    pythonFiles.push(file);
  }

  if (biomeMatchers.includes(ext)) {
    biomeFiles.push(file);
  }

  if (eslintMatchers.includes(ext)) {
    eslintFiles.push(file);
  }
}

let exitCode = 0;

const runTrackedCommand = (command, args, files, toolLabel) => {
  if (files.length === 0) {
    return;
  }

  logInfo(`[lint-changed] Running ${toolLabel} on ${files.length} file(s).`);
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    env: process.env,
    stdio: "inherit",
  });

  if (typeof result.status === "number" && result.status !== 0) {
    exitCode = result.status;
  }
};

if (pythonFiles.length > 0) {
  const args = ["run", "ruff", "check"];
  if (options.fix) {
    args.push("--fix");
  }
  args.push("--");
  args.push(...pythonFiles);
  runTrackedCommand(uvBinary, args, pythonFiles, "Ruff");
}

if (biomeFiles.length > 0) {
  const args = ["exec", "biome", "check", "--no-errors-on-unmatched"];
  if (options.fix) {
    args.push("--write");
  }
  args.push(...biomeFiles);
  runTrackedCommand(npmExec, args, biomeFiles, "Biome");
}

if (eslintFiles.length > 0) {
  const args = [
    "exec",
    "eslint",
    "--max-warnings=0",
    "--cache",
    "--cache-location",
    ".cache/eslint",
  ];
  if (options.fix) {
    args.push("--fix");
  }
  args.push(...eslintFiles);
  runTrackedCommand(npmExec, args, eslintFiles, "ESLint");
}

if (exitCode === 0) {
  logInfo("[lint-changed] Completed without errors.");
}

process.exit(exitCode);
