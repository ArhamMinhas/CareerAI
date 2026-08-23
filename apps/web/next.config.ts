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
    // How long optimized images stay cached at the edge before revalidating (seconds).
    minimumCacheTTL: 60 * 60 * 24 * 365, // 1 year — these are static placeholder avatars
  },

  productionBrowserSourceMaps: false,

  experimental: {
    // Tree-shakes barrel-file imports for these packages instead of pulling in the whole
    // module graph per import.
    optimizePackageImports: ["@radix-ui/react-accordion", "@react-three/fiber", "recharts"],
  },

  compress: true,
  poweredByHeader: false,
};

export default nextConfig;
