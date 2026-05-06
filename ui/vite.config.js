import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";
import fs from "node:fs";

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
  server: (() => {
    const host = process.env.VITE_HOST ?? "0.0.0.0";
    const port = Number(process.env.VITE_PORT ?? 5173);
    const hmrHost = process.env.VITE_HMR_HOST;
    const hmrPort = process.env.VITE_HMR_PORT
      ? Number(process.env.VITE_HMR_PORT)
      : undefined;
    const keyPath = process.env.VITE_SSL_KEY_PATH;
    const certPath = process.env.VITE_SSL_CERT_PATH;

    const hasCertConfig = Boolean(keyPath && certPath);
    const canUseHttps =
      hasCertConfig && fs.existsSync(keyPath) && fs.existsSync(certPath);

    if (hasCertConfig && !canUseHttps) {
      console.warn(
        `[vite] HTTPS certificate files were configured but not found. Falling back to HTTP. key=${keyPath} cert=${certPath}`,
      );
    }

    const https = canUseHttps
      ? {
          key: fs.readFileSync(keyPath),
          cert: fs.readFileSync(certPath),
        }
      : false;

    return {
      host,
      port,
      https,
      hmr: hmrHost || hmrPort
        ? {
            host: hmrHost,
            protocol: https ? "wss" : "ws",
            clientPort: hmrPort,
          }
        : undefined,
    };
  })(),
});
