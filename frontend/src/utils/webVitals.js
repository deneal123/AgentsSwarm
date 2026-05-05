import { getCLS, getFID, getLCP, getFCP, getTTFB, onINP } from "web-vitals";

const THRESHOLDS = {
  LCP: { good: 2500, needsImprovement: 4000 },
  FID: { good: 100, needsImprovement: 300 },
  CLS: { good: 0.1, needsImprovement: 0.25 },
  FCP: { good: 1800, needsImprovement: 3000 },
  TTFB: { good: 800, needsImprovement: 1800 },
  INP: { good: 200, needsImprovement: 500 },
};

const getRating = (name, value) => {
  const threshold = THRESHOLDS[name];
  if (!threshold) return "unknown";
  if (value <= threshold.good) return "good";
  if (value <= threshold.needsImprovement) return "needs-improvement";
  return "poor";
};

const formatMetric = (metric) => ({
  name: metric.name,
  value: metric.value,
  rating: getRating(metric.name, metric.value),
  delta: metric.delta,
  metric_id: metric.id,
  navigation_type: metric.navigationType,
  recorded_at: new Date().toISOString(),
});

const logMetric = (metric) => {
  const colors = {
    good: "color: #0cce6b",
    "needs-improvement": "color: #ffa400",
    poor: "color: #ff4e42",
    unknown: "color: #gray",
  };
  const style = colors[metric.rating] || colors.unknown;
  console.log(`%c[Web Vitals] ${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})`, style);
};

const handleMetric = (metric, options = {}) => {
  const formatted = formatMetric(metric);
  if (process.env.NODE_ENV === "development" || options.debug) {
    logMetric(formatted);
  }
  if (typeof options.onMetric === "function") {
    options.onMetric(formatted);
  }
};

export const reportWebVitals = (options = {}) => {
  const handler = (metric) => handleMetric(metric, options);
  getCLS(handler);
  getFID(handler);
  getLCP(handler);
  getFCP(handler);
  getTTFB(handler);
  onINP(handler);
};

export const getThresholds = () => ({ ...THRESHOLDS });

const metricsStore = {};

export const collectMetrics = () => {
  reportWebVitals({
    debug: false,
    sendToServer: false,
    onMetric: (metric) => {
      metricsStore[metric.name] = metric;
    },
  });
};

export const getCollectedMetrics = () => ({ ...metricsStore });

export default reportWebVitals;
