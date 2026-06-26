/** @type {import('next').NextConfig} */
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://localhost:8000';

const nextConfig = {
  transpilePackages: ['framer-motion'],
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

module.exports = nextConfig;
