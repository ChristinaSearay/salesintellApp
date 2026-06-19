/** @type {import('next').NextConfig} */

// The Python engine (server.py / `uv run app`) serves the JSON API on :8000.
// We proxy /api/* to it so the browser calls same-origin (no CORS) and the
// React frontend never needs to know the backend's address.
const BACKEND = process.env.SEARAY_API || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

export default nextConfig;
