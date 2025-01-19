import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from 'next/constants';

const nextConfig: NextConfig = (phase: string) => {
  let env = {};

  // Dynamically set environment variables based on deployment type
  if (phase === PHASE_PRODUCTION_BUILD && process.env.NEXT_PUBLIC_DEPLOYMENT_TYPE === 'mlops') {
    env = {
      NEXT_PUBLIC_DEPLOYMENT_TYPE: 'mlops',
    };
  } else if (phase === PHASE_PRODUCTION_BUILD && process.env.NEXT_PUBLIC_DEPLOYMENT_TYPE === 'devops') {
    env = {
      NEXT_PUBLIC_DEPLOYMENT_TYPE: 'devops',
    };
  }

  return {
    images: {
      dangerouslyAllowSVG: true,
      remotePatterns: ["seito.lavbic.net"],
      contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    },
    env,
  };
};

export default nextConfig;