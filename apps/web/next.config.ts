import type { NextConfig } from "next";

const config: NextConfig = {
  transpilePackages: ["@ogas/shared", "@ogas/features", "@ogas/ui", "@ogas/core", "@ogas/platform"],
};

export default config;
