import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Other config options */
  devIndicators: false,
  eslint: {
    ignoreDuringBuilds: true,
  },
  async headers() {
    return [
      {
        source: "/(.*)", // match all routes
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; " +
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'; " +
              "style-src 'self' 'unsafe-inline'; " +
              "img-src 'self' data:; " +
              "connect-src 'self'; " +
              "object-src 'none'; " +
              "base-uri 'self'; " +
              "frame-ancestors 'none'; " +
              "form-action 'self';",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
