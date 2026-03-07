import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Output a standalone build for smaller Docker images
  output: 'standalone',
  async rewrites() {
    return [
      {
        // When running in Docker, 'api' refers to the backend service
        source: '/v1/:path*',
        destination: process.env.BACKEND_URL ? `${process.env.BACKEND_URL}/v1/:path*` : 'http://localhost:8000/v1/:path*',
      },
      {
        source: '/health',
        destination: process.env.BACKEND_URL ? `${process.env.BACKEND_URL}/health` : 'http://localhost:8000/health',
      },
    ];
  },
};

export default nextConfig;
