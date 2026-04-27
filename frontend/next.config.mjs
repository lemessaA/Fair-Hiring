/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000"
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/:path*`,
      },
    ]
  },
}

export default nextConfig
