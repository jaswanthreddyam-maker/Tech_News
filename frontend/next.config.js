const rawTarget = process.env.API_PROXY_TARGET || process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;
const isProd = process.env.NODE_ENV === 'production' || process.env.VERCEL === '1';
const defaultTarget = isProd ? 'https://technews-production-d18d.up.railway.app' : 'http://localhost:8000';
let baseTarget = (rawTarget && rawTarget.startsWith('http')) ? rawTarget : defaultTarget;
baseTarget = baseTarget.trim().replace(/\/+$/, '');
if (baseTarget.endsWith('/api/v1')) {
  baseTarget = baseTarget.slice(0, -7).replace(/\/+$/, '');
}
const apiProxyTarget = baseTarget;

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
