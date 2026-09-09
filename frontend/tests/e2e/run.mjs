import { spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testRoot = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(testRoot, "../..");
const runtimeId = crypto.createHash("sha256").update(frontendRoot.toLowerCase()).digest("hex").slice(0, 12);
const runtimeRoot = path.join(os.tmpdir(), `store-admin-e2e-${runtimeId}`);

function removeRuntime() {
  if (path.dirname(runtimeRoot) !== path.resolve(os.tmpdir()) || !/^store-admin-e2e-[a-f0-9]{12}$/.test(path.basename(runtimeRoot))) {
    throw new Error(`Refusing to remove unexpected E2E path: ${runtimeRoot}`);
  }
  fs.rmSync(runtimeRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 150 });
}

removeRuntime();
let exitCode = 1;
try {
  const cli = path.resolve(frontendRoot, "node_modules/@playwright/test/cli.js");
  const forwardedArguments = process.argv.slice(2).filter((argument) => argument !== "--");
  const result = spawnSync(process.execPath, [cli, "test", ...forwardedArguments], {
    cwd: frontendRoot,
    stdio: "inherit",
    env: process.env,
  });
  exitCode = result.status ?? 1;
} finally {
  removeRuntime();
}
process.exit(exitCode);
