import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server for the Cloud Run Docker image.
  output: "standalone",
  // No dev badge in screenshots and the demo video.
  devIndicators: false,
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
