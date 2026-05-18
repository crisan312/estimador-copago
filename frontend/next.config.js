/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // INTERNAL_API_URL: Docker-internal URL for server-side proxy (e.g. http://api:8000)
    // Falls back to NEXT_PUBLIC_API_URL for local dev without Docker
    const apiUrl = process.env.INTERNAL_API_URL ||
                   process.env.NEXT_PUBLIC_API_URL ||
                   "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
