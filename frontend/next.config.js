/** @type {import('next').NextConfig} */
const rawTarget = process.env.API_PROXY_TARGET || process.env.NEXT_PUBLIC_API_URL;
const apiProxyTarget = (rawTarget && rawTarget.startsWith('http')) ? rawTarget : 'http://localhost:8000';

const nextConfig = {
  experimental: {
    optimizePackageImports: ['lucide-react', 'date-fns'],
  },
  images: {
    unoptimized: true,
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
