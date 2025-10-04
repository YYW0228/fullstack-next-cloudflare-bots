/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // 禁用构建缓存以避免大文件
  webpack: (config: any, { isServer }: { isServer: boolean }) => {
    config.cache = false;
    return config;
  },
}

module.exports = nextConfig
