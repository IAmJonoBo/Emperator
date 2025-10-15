#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const { error: logError, warn: logWarn } = globalThis.console;

const repoRoot = process.cwd();
const sarifDirectory = path.join(repoRoot, ".sarif");
mkdirSync(sarifDirectory, { recursive: true });

const npmExec = process.env.npm_execpath ?? "pnpm";
let exitCode = 0;

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
  logError(
    "uv is required to generate Ruff SARIF output. Install uv (https://docs.astral.sh/uv/) and retry."
  );
  process.exit(1);
}

const runCommand = (command, args, options = {}) => {
  const result = spawnSync(command, args, {
    env: process.env,
    stdio: "inherit",
    ...options,
  });

  if (typeof result.status === "number" && result.status !== 0) {
    exitCode = result.status;
  }

  return result;
};

const captureCommand = (command, args) => {
  const result = spawnSync(command, args, {
    env: process.env,
    stdio: ["ignore", "pipe", "inherit"],
    encoding: "utf8",
  });

  if (typeof result.status === "number" && result.status !== 0) {
    exitCode = result.status;
  }

  return result;
};

const writeJson = (relativePath, payload) => {
  const target = path.join(sarifDirectory, relativePath);
  writeFileSync(target, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
};

const computePosition = (source, offset) => {
  if (typeof offset !== "number" || offset < 0) {
    return { line: 1, column: 1 };
  }
  const slice = source.slice(0, offset);
  const segments = slice.split(/\r?\n/);
  const line = segments.length;
  const column = (segments.pop() ?? "").length + 1;
  return { line, column };
};

const toBiomeSarif = (payload) => {
  const diagnostics = Array.isArray(payload?.diagnostics) ? payload.diagnostics : [];

  const biomeVersionResult = captureCommand(npmExec, ["exec", "biome", "--version"]);
  const biomeVersion = biomeVersionResult.stdout?.trim() ?? undefined;

  const results = diagnostics.map((diagnostic) => {
    const fragments = Array.isArray(diagnostic?.message)
      ? diagnostic.message.map((part) => part?.content ?? "")
      : [diagnostic?.description ?? "Biome reported an issue."];
    const message = fragments.join("");
    const category = diagnostic?.category ?? diagnostic?.source ?? "biome";
    const severity =
      diagnostic?.severity === "error"
        ? "error"
        : diagnostic?.severity === "warning"
          ? "warning"
          : "note";

    const location = diagnostic?.location ?? {};
    const filePath =
      typeof location?.path === "string"
        ? location.path
        : typeof location?.path?.file === "string"
          ? location.path.file
          : undefined;
    const absolutePath = filePath ? path.resolve(repoRoot, filePath) : repoRoot;
    const relativePath = path.relative(repoRoot, absolutePath) || path.basename(absolutePath);

    const span = Array.isArray(location?.span) ? location.span : undefined;
    let region;
    if (span && typeof span[0] === "number") {
      const source = location?.sourceCode ?? "";
      const start = computePosition(source, span[0]);
      const end = computePosition(source, span[1] ?? span[0]);
      region = {
        startLine: start.line,
        startColumn: start.column,
        endLine: end.line,
        endColumn: end.column,
      };
    }
    if (!region) {
      region = { startLine: 1, startColumn: 1 };
    }

    return {
      ruleId: Array.isArray(category) ? category.join("/") : category,
      level: severity,
      message: { text: message },
      locations: [
        {
          physicalLocation: {
            artifactLocation: { uri: relativePath.replace(/\\/g, "/") },
            region,
          },
        },
      ],
    };
  });

  return {
    version: "2.1.0",
    $schema: "https://json.schemastore.org/sarif-2.1.0.json",
    runs: [
      {
        tool: {
          driver: {
            name: "Biome",
            version: biomeVersion,
            informationUri: "https://biomejs.dev",
          },
        },
        results,
      },
    ],
  };
};

const runRuffSarif = () => {
  const target = path.join(sarifDirectory, "ruff.sarif");
  runCommand(uvBinary, [
    "run",
    "ruff",
    "check",
    ".",
    "--output-format",
    "sarif",
    "--output-file",
    target,
  ]);
};

const runBiomeSarif = () => {
  const result = captureCommand(npmExec, [
    "exec",
    "biome",
    "check",
    "--reporter",
    "json",
    "--no-errors-on-unmatched",
    ".",
  ]);

  const output = result.stdout ?? "";
  const start = output.indexOf("{");
  const end = output.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    logWarn("Biome JSON reporter did not produce parseable output.");
    return;
  }

  try {
    const parsed = JSON.parse(output.slice(start, end + 1));
    const sarif = toBiomeSarif(parsed);
    writeJson("biome.sarif", sarif);
  } catch (parseError) {
    logError("Failed to convert Biome diagnostics to SARIF", parseError);
  }
};

const runEslintSarif = () => {
  const target = path.join(sarifDirectory, "eslint.sarif");
  runCommand(npmExec, [
    "exec",
    "eslint",
    "--max-warnings=0",
    "--no-warn-ignored",
    "--cache",
    "--cache-location",
    ".cache/eslint",
    "--format",
    "@microsoft/eslint-formatter-sarif",
    "--output-file",
    target,
    ".",
  ]);
};

runRuffSarif();
runBiomeSarif();
runEslintSarif();

process.exitCode = exitCode;
