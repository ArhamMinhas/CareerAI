import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for the production Docker image (infrastructure/docker/Dockerfile.web) —
  // docs/DEPLOYMENT.md §3.
  output: "standalone",
  images: {
    remotePatterns: [
      // Placeholder avatars for the Phase 2 testimonials section — replaced once real user
      // avatars exist (Supabase Storage, per docs/SEO.md §2.7 image optimization).
      { protocol: "https", hostname: "i.pravatar.cc" },
    ],
  },
};

export default nextConfig;
