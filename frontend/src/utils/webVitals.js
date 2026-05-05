import { getCLS, getFID, getLCP, getFCP, getTTFB, onINP } from "web-vitals";

const THRESHOLDS = {
  LCP: { good: 2500, needsImprovement: 4000 },
  FID: { good: 100, needsImprovement: 300 },
  CLS: { good: 0.1, needsImprovement: 0.25 },
  FCP: { good: 1800, needsImprovement: 3000 },
  TTFB: { good: 800, needsImprovement: 1800 },
  INP: { good: 200, needsImprovement: 500 },
};

const ANALYTICS_ENDPOINT = "/api/analytics/vitals";
const PAYLOAD_VERSION = "1.0";
const SAMPLE_RATE = Number.parseFloat(process.env.REACT_APP_VITALS_SAMPLE_RATE || "0.3");
const BATCH_SIZE = 5;
const BATCH_INTERVAL_MS = 10000;
const queue = [];
let flushTimer = null;

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

const hashString = (input) => {
  const value = String(input || "anonymous");
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) + hash) + value.charCodeAt(index);
    hash |= 0;
  }
  return `anon_${Math.abs(hash).toString(16)}`;
};

const getAnonymousUserId = () => {
  const rawId = localStorage.getItem("user_id") || localStorage.getItem("email") || "guest";
  return hashString(rawId);
};

const sendBatch = (events) => {
  if (!events.length) return;
  const payload = {
    version: PAYLOAD_VERSION,
    sampled: true,
    session_id: hashString(`${performance.timeOrigin || Date.now()}`),
    user_id_hash: getAnonymousUserId(),
    page: window.location.pathname,
    user_agent: navigator.userAgent,
    events,
  };

  const body = JSON.stringify(payload);
  const blob = new Blob([body], { type: "application/json" });

  if (typeof navigator.sendBeacon === "function") {
    const sent = navigator.sendBeacon(ANALYTICS_ENDPOINT, blob);
    if (sent) return;
  }

  fetch(ANALYTICS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => null);
};

const flushQueue = () => {
  if (!queue.length) return;
  const batch = queue.splice(0, queue.length);
  sendBatch(batch);
};

const scheduleFlush = () => {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    flushQueue();
  }, BATCH_INTERVAL_MS);
};

const sendToAnalytics = (metric) => {
  if (Math.random() > SAMPLE_RATE) return;
  queue.push(metric);
  if (queue.length >= BATCH_SIZE) {
    flushQueue();
    return;
  }
  scheduleFlush();
};

const handleMetric = (metric, options = {}) => {
  const formatted = formatMetric(metric);
  if (process.env.NODE_ENV === "development" || options.debug) {
    logMetric(formatted);
  }
  if (options.sendToServer !== false) {
    sendToAnalytics(formatted);
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

let metricsStore = {};

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

window.addEventListener("beforeunload", () => {
  flushQueue();
});

export default reportWebVitals;
