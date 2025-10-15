#!/usr/bin/env node
import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { parseAllDocuments } from "yaml";

const { error: logError, log: logInfo } = globalThis.console;

const args = process.argv.slice(2).filter((arg) => arg !== "--");
const SUPPORTED_FLAGS = new Set(["--check"]);
const unsupported = args.filter((arg) => !SUPPORTED_FLAGS.has(arg));
if (unsupported.length > 0) {
  logError(`Unknown format option(s): ${unsupported.join(", ")}`);
  process.exit(1);
}
const checkMode = args.includes("--check");

const parsePositiveInteger = (value, fallback) => {
  if (typeof value !== "string" || value.trim() === "") {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const indent = parsePositiveInteger(process.env.FORMAT_YAML_INDENT, 2);
const lineWidth = parsePositiveInteger(process.env.FORMAT_YAML_WIDTH, 120);

const IGNORED_DIRECTORIES = [
  ".git",
  ".pnpm-store",
  ".venv",
  "build",
  "dist",
  "node_modules",
  "site",
  ".cache",
];

const LOCKFILE_BASENAMES = new Set(["pnpm-lock.yaml", "uv.lock"]);
const includeLockfiles = process.env.FORMAT_YAML_INCLUDE_LOCKS === "1";

const shouldIgnore = (relativePath) => {
  if (!relativePath) {
    return false;
  }
  const normalised = relativePath.split(path.sep).join("/");
  return IGNORED_DIRECTORIES.some((ignore) => {
    if (normalised === ignore) {
      return true;
    }
    return normalised.startsWith(`${ignore}/`);
  });
};

const collectYamlFiles = async (rootDir) => {
  const stack = [rootDir];
  const files = [];

  while (stack.length > 0) {
    const current = stack.pop();
    let entries;
    try {
      entries = await readdir(current, { withFileTypes: true });
    } catch (error) {
      logError(
        `[format-yaml] Unable to read directory ${path.relative(rootDir, current) || "."}`,
        error
      );
      process.exitCode = 1;
      continue;
    }

    for (const entry of entries) {
      const absolute = path.join(current, entry.name);
      const relative = path.relative(rootDir, absolute);
      if (shouldIgnore(relative)) {
        continue;
      }

      if (entry.isDirectory()) {
        stack.push(absolute);
        continue;
      }

      if (!entry.isFile()) {
        continue;
      }

      if (entry.name.endsWith(".yaml") || entry.name.endsWith(".yml")) {
        const relativeFile = relative || entry.name;
        if (!includeLockfiles && LOCKFILE_BASENAMES.has(entry.name)) {
          continue;
        }
        files.push(relativeFile);
      }
    }
  }

  return files;
};

const reportYamlErrors = (file, errors) => {
  for (const error of errors) {
    logError(`[format-yaml] ${file}: ${error.message}`);
  }
  if (!process.exitCode) {
    process.exitCode = 1;
  }
};

const run = async () => {
  const cwd = process.cwd();
  const files = await collectYamlFiles(cwd);

  if (files.length === 0) {
    return;
  }

  let formattedCount = 0;
  const flaggedFiles = [];
  const formatOptions = {
    indent,
    lineWidth,
  };

  for (const file of files) {
    const absolutePath = path.join(cwd, file);
    let original;
    try {
      original = await readFile(absolutePath, "utf8");
    } catch (error) {
      logError(`[format-yaml] Failed to read ${file}`, error);
      process.exitCode = 1;
      continue;
    }

    const normalisedOriginal = original.replace(/\r\n/g, "\n");

    let documents;
    try {
      documents = parseAllDocuments(normalisedOriginal, {
        prettyErrors: true,
      });
    } catch (error) {
      logError(`[format-yaml] Failed to parse ${file}`, error);
      process.exitCode = 1;
      continue;
    }

    if (documents.length === 0) {
      continue;
    }

    let hasErrors = false;
    for (const document of documents) {
      if (document.errors.length > 0) {
        reportYamlErrors(file, document.errors);
        hasErrors = true;
      }
    }

    if (hasErrors) {
      continue;
    }

    const formatted = documents.map((document) => document.toString(formatOptions)).join("");
    const normalisedFormatted = formatted.endsWith("\n") ? formatted : `${formatted}\n`;

    if (normalisedFormatted === normalisedOriginal) {
      continue;
    }

    const newlineStyle = original.includes("\r\n") ? "\r\n" : "\n";
    const finalOutput =
      newlineStyle === "\n"
        ? normalisedFormatted
        : normalisedFormatted.replace(/\n/g, newlineStyle);

    if (checkMode) {
      flaggedFiles.push(file);
      continue;
    }

    try {
      await writeFile(absolutePath, finalOutput, "utf8");
      formattedCount += 1;
    } catch (error) {
      logError(`[format-yaml] Failed to write ${file}`, error);
      process.exitCode = 1;
    }
  }

  if (checkMode) {
    if (flaggedFiles.length > 0 && !process.exitCode) {
      process.exitCode = 1;
    }
    if (flaggedFiles.length > 0) {
      logError(
        `[format-yaml] ${flaggedFiles.length} YAML file(s) require formatting:\n${flaggedFiles
          .map((file) => `  - ${file}`)
          .join("\n")}\n`
      );
    }
    return;
  }

  if (formattedCount > 0) {
    logInfo(`[format-yaml] Updated ${formattedCount} YAML file(s)`);
  }
};

run().catch((error) => {
  logError("[format-yaml] Unexpected failure", error);
  process.exitCode = 1;
});
