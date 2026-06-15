/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fully static export -> deployable to Vercel / GitHub Pages / any static host
  // with no Node server. The dashboard imports its data JSON at build time.
  output: "export",
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
