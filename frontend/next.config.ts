import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "statiq-images-prod.s3.ap-south-1.amazonaws.com" },
      { protocol: "https", hostname: "d3orevttu06iqr.cloudfront.net" },
      { protocol: "https", hostname: "**.cloudfront.net" },
    ],
  },
};

export default nextConfig;
