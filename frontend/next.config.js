/** @type {import('next').NextConfig} */
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000';

const nextConfig = {
  experimental: {
    optimizePackageImports: ['lucide-react', 'date-fns'],
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: '**',
      },
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        // Proxy all /api/v1/ requests to FastAPI.
        // Host-run dev uses localhost; Docker sets API_PROXY_TARGET=backend.
        source: '/api/v1/:path*',
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
    ];
  },
};

const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

module.exports = withBundleAnalyzer(nextConfig);
