import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";

function resolveAppVersion() {
  try {
    const commitDate = execSync("git log -1 --date=format:%Y.%m.%d --format=%cd", {
      encoding: "utf8",
    }).trim();
    const shortSha = execSync("git rev-parse --short HEAD", { encoding: "utf8" }).trim();
    if (commitDate && shortSha) {
      return `${commitDate}-${shortSha}`;
    }
  } catch {
    // Fall back for environments without git metadata.
  }
  return "unknown";
}

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(resolveAppVersion()),
  },
});
