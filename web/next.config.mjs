/** @type {import('next').NextConfig} */
const API = process.env.CRICINTEL_API || "http://127.0.0.1:8000";
export default {
  reactStrictMode: true,
  async redirects() {
    return [{ source: "/favicon.ico", destination: "/icon.svg", permanent: true }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
