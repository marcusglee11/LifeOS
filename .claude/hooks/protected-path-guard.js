#!/usr/bin/env node
/**
 * PreToolUse hook: block Write/Edit to governance-protected paths.
 * Reads config/governance/protected_artefacts.json at runtime.
 * Fail-open on any error (missing file, parse failure, etc.).
 */
"use strict";

const fs = require("fs");
const path = require("path");

const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();

function main() {
  let input;
  try {
    input = JSON.parse(require("fs").readFileSync("/dev/stdin", "utf8"));
  } catch {
    process.exit(0); // fail-open: can't parse stdin
  }

  const filePath = (input.tool_input && input.tool_input.file_path) || "";
  if (!filePath) {
    process.exit(0); // no file_path means nothing to guard
  }

  // Normalize: resolve absolute, then make relative to project dir
  const absTarget = path.resolve(PROJECT_DIR, filePath);
  const relativePath = path.relative(PROJECT_DIR, absTarget).replace(/\\/g, "/");

  // Load protected paths
  let config;
  try {
    const raw = fs.readFileSync(
      path.join(PROJECT_DIR, "config", "governance", "protected_artefacts.json"),
      "utf8"
    );
    config = JSON.parse(raw);
  } catch {
    process.exit(0); // fail-open: config missing or unparseable
  }

  const protectedPaths = config.protected_paths || [];
  const lockedBy = config.locked_by || "governance policy";

  for (const pp of protectedPaths) {
    const normalized = pp.replace(/\\/g, "/");
    if (
      relativePath === normalized ||                          // exact match
      relativePath.startsWith(normalized + "/")               // directory child (boundary-safe)
    ) {
      process.stderr.write(
        `BLOCKED: "${relativePath}" is governance-protected.\n` +
        `Protected by: ${lockedBy}\n` +
        `To modify, you need explicit Council approval. Ask the user first.\n`
      );
      process.exit(2);
    }
  }

  process.exit(0); // not protected, allow
}

main();
