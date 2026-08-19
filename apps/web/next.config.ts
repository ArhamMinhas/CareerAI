import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for the production Docker image (infrastructure/docker/Dockerfile.web) —
  // docs/DEPLOYMENT.md §3.
  output: "standalone",
};

export default nextConfig;
