import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  turbopack: {
    // Pin the workspace root to this project to silence the multi-lockfile
    // inference warning (a stray lockfile lives in $HOME).
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
