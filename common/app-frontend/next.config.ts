import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants";

const nextConfig = (phase: string): NextConfig => {
  const isProductionBuild = phase === PHASE_PRODUCTION_BUILD;
  const deploymentType = process.env.NEXT_PUBLIC_DEPLOYMENT_TYPE || "default";

  const env = {
    NEXT_PUBLIC_DEPLOYMENT_TYPE: deploymentType,
  };

  const distDir =
    isProductionBuild && (deploymentType === "mlops" || deploymentType === "devops")
      ? `.next-${deploymentType}`
      : ".next";

  return {
    distDir,
    images: {
      dangerouslyAllowSVG: true,
      remotePatterns: [
        {
          protocol: "https",
          hostname: "seito.lavbic.net",
        },
      ],
      contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    },
    env,
  };
};

export default nextConfig;