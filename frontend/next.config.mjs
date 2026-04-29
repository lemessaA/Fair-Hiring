import os from "node:os"

/** @type {import('next').NextConfig} */
function lanIpv4Hosts() {
  /** Non-loopback IPv4s so LAN access (e.g. http://10.x.x.x:3000) is allowed for Turbopack/HMR. */
  const hosts = new Set()
  for (const nets of Object.values(os.networkInterfaces())) {
    for (const n of nets ?? []) {
      if (n?.family === "IPv4" && !n.internal && n.address) hosts.add(n.address)
    }
  }
  return [...hosts]
}

const fromEnv = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean)

const allowedDevOrigins =
  process.env.NODE_ENV === "production"
    ? fromEnv
    : [...new Set([...fromEnv, ...lanIpv4Hosts(), "localhost", "127.0.0.1"])]

const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  ...(allowedDevOrigins.length > 0 ? { allowedDevOrigins } : {}),
  async rewrites() {
    // Client calls `/api/*` on the Next host; these rewrites proxy to FastAPI (local or FastAPI Cloud).
    // On Vercel set BACKEND_URL to your API origin, e.g. https://your-app.fastapicloud.dev (no trailing slash).
    const raw = process.env.BACKEND_URL || "http://127.0.0.1:8000"
    const backend = raw.replace(/\/$/, "")
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/:path*`,
      },
    ]
  },
}

export default nextConfig
