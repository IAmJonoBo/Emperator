#!/usr/bin/env node
import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { parseDocument } from "yaml";

const { error: logError, log: logInfo } = globalThis.console;

const IGNORED_DIRECTORIES = [
  ".git",
  ".pnpm-store",
  ".venv",
  "build",
  "dist",
  "emperator_specs/site",
  "node_modules",
  "site",
  ".cache",
];

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
        files.push(relative || entry.name);
      }
    }
  }

  return files;
};

const run = async () => {
  const cwd = process.cwd();
  const files = await collectYamlFiles(cwd);

  if (files.length === 0) {
    return;
  }

  let formattedCount = 0;
  for (const file of files) {
    try {
      const original = await readFile(path.join(cwd, file), "utf8");
      const doc = parseDocument(original, {
        prettyErrors: true,
      });
      const formatted = doc.toString({
        indent: 2,
        lineWidth: 120,
      });
      if (formatted !== original) {
        await writeFile(path.join(cwd, file), formatted, "utf8");
        formattedCount += 1;
      }
    } catch (error) {
      logError(`[format-yaml] Failed to format ${file}`, error);
      process.exitCode = 1;
    }
  }

  if (formattedCount > 0) {
    logInfo(`[format-yaml] Updated ${formattedCount} YAML file(s)`);
  }
};

run().catch((error) => {
  logError("[format-yaml] Unexpected failure", error);
  process.exitCode = 1;
});
