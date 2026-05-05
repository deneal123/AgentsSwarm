const path = require("path");

const resolveSrc = (segment = "") => path.join(__dirname, "src", segment);

const alias = {
  "@": resolveSrc(""),
  "@ui": resolveSrc("ui"),
  "@features": resolveSrc("features"),
  "@pages": resolveSrc("pages"),
  "@utils": resolveSrc("utils"),
  "@theme": resolveSrc("theme"),
  "@context": resolveSrc("context"),
  "@constants": resolveSrc("constants"),
  "@api": resolveSrc("API"),
  "@hooks": resolveSrc("hooks"),
};

const moduleNameMapper = Object.entries(alias).reduce((mapper, [key, target]) => {
  const escapedKey = key.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
  mapper[`^${escapedKey}/(.*)$`] = `${target}/$1`;
  mapper[`^${escapedKey}$`] = target;
  return mapper;
}, {});

module.exports = {
  webpack: {
    alias,
    configure: (webpackConfig, { env }) => {
      // Оптимизация только для production
      if (env === "production") {
        // Разделение бандла на чанки для лучшего кеширования
        webpackConfig.optimization.splitChunks = {
          chunks: "all",
          minSize: 20000,
          maxSize: 244000,
          cacheGroups: {
            // Основные вендоры
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: "vendors",
              chunks: "all",
              priority: 10,
            },
            // Chakra UI в отдельный чанк
            chakra: {
              test: /[\\/]node_modules[\\/](@chakra-ui|@emotion|framer-motion)[\\/]/,
              name: "chakra",
              chunks: "all",
              priority: 20,
            },
            // Графики и визуализация в отдельный чанк
            charts: {
              test: /[\\/]node_modules[\\/](recharts|d3)[\\/]/,
              name: "charts",
              chunks: "all",
              priority: 20,
            },
            // React в отдельный чанк
            react: {
              test: /[\\/]node_modules[\\/](react|react-dom|react-router|react-router-dom)[\\/]/,
              name: "react",
              chunks: "all",
              priority: 30,
            },
          },
        };

        // Включаем tree shaking
        webpackConfig.optimization.usedExports = true;
        webpackConfig.optimization.sideEffects = true;

        // Настройка Terser для агрессивной минификации
        const TerserPlugin = require("terser-webpack-plugin");
        webpackConfig.optimization.minimizer = [
          new TerserPlugin({
            terserOptions: {
              parse: {
                ecma: 8,
              },
              compress: {
                ecma: 5,
                warnings: false,
                comparisons: false,
                inline: 2,
                drop_console: true,        // Удаляем console.log
                drop_debugger: true,       // Удаляем debugger
                pure_funcs: ["console.info", "console.debug", "console.warn"],
              },
              mangle: {
                safari10: true,
              },
              output: {
                ecma: 5,
                comments: false,           // Удаляем комментарии
                ascii_only: true,
              },
            },
            extractComments: false,
          }),
        ];
      }

      return webpackConfig;
    },
  },
  jest: {
    configure: {
      moduleNameMapper,
    },
  },
};
