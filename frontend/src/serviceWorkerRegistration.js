// Simple service worker registration helper
// Register the service worker only in production builds and when supported

export function registerServiceWorker() {
  if (typeof window === "undefined") return;
  if (!("serviceWorker" in navigator)) return;

  if (process.env.NODE_ENV !== "production") return;

  const swUrl = `${process.env.PUBLIC_URL || "."}/service-worker.js`;

  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      // Registration successful
      console.info("[SW] Registered:", registration.scope);

      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (!installingWorker) return;
        installingWorker.onstatechange = () => {
          if (installingWorker.state === "installed") {
            if (navigator.serviceWorker.controller) {
              // New content available, prompt user or auto-refresh
              console.info("[SW] New content available; please refresh.");
            } else {
              console.info("[SW] Content cached for offline use.");
            }
          }
        };
      };
    })
    .catch((err) => {
      console.warn("[SW] Registration failed:", err);
    });
}

export function unregisterServiceWorker() {
  if (typeof window === "undefined") return;
  if (!("serviceWorker" in navigator)) return;

  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((reg) => reg.unregister());
  });
}
