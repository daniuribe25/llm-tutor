import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Lockfiles above this folder can make Turbopack pick the wrong root; standalone
// output must be flat so the Docker image can COPY `.next/standalone`.
const turbopackRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: turbopackRoot,
  },
};

export default nextConfig;
