/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    // Only add rewrites if API URL is configured
    if (!apiUrl || apiUrl === 'http://localhost:8000') {
      return [
        {
          source: '/api/backend/:path*',
          destination: 'http://localhost:8000/api/v1/:path*',
        },
      ];
    }
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
