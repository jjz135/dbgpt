/** @type {import('next').NextConfig} */
const CopyPlugin = require("copy-webpack-plugin");
const MonacoWebpackPlugin = require("monaco-editor-webpack-plugin");
const path = require("path");
const nextConfig = {
  experimental: {
    esmExternals: "loose",
    // 禁用 worker threads，使用进程池
    workerThreads: false,
    // 增加页面数据收集超时
    pageDataCollectionTimeout: 60000,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // 降低并行度，避免 Static worker SIGTERM 错误
  parallelism: 1,
  // 增加构建超时时间
  staticPageGenerationTimeout: 120,
  env: {
    API_BASE_URL: process.env.API_BASE_URL,
    GITHUB_CLIENT_ID: process.env.GITHUB_CLIENT_ID,
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
    GET_USER_URL: process.env.GET_USER_URL,
    LOGIN_URL: process.env.LOGIN_URL,
    LOGOUT_URL: process.env.LOGOUT_URL,
  },
  trailingSlash: true,
  images: { unoptimized: true },
  skipTrailingSlashRedirect: true,
  webpack: (config, { isServer }) => {
    config.resolve.fallback = { fs: false };
    // 解决 d3-color ESM/CommonJS 兼容性问题
    config.resolve.alias = {
      ...config.resolve.alias,
      'd3-color': path.join(__dirname, 'node_modules/d3-color'),
    };
    
    // 优化构建性能，减少内存占用
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          maxInitialRequests: 10,
          maxSize: 244 * 1024,
        },
      };
    }
    
    if (!isServer) {
      config.plugins.push(
        new CopyPlugin({
          patterns: [
            {
              from: path.join(
                __dirname,
                "node_modules/@oceanbase-odc/monaco-plugin-ob/worker-dist/"
              ),
              to: "static/ob-workers",
            },
          ],
        })
      );
      // 添加 monaco-editor-webpack-plugin 插件
      config.plugins.push(
        new MonacoWebpackPlugin({
          // 你可以在这里配置插件的选项，例如：
          languages: ["sql"],
          filename: "static/[name].worker.js",
        })
      );
    }
    return config;
  },
};

const withTM = require("next-transpile-modules")([
  "@berryv/g2-react",
  "@antv/g2",
  "react-syntax-highlighter",
  "@antv/g6",
  "@antv/graphin",
  "@antv/gpt-vis",
  // 解决 ESM/CommonJS 兼容性问题
  "@antv/g",
  "@antv/g-lite",
  "@antv/g-camera-api",
  "d3-color",
]);

module.exports = withTM({
  ...nextConfig,
});
