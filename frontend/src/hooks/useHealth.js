import { useEffect, useState } from "react";
import client from "@api/client";
import extractErrorInfo from "@utils/errorHandler";

const DEFAULT_STATUS = { ok: null, details: null, error: null };
const isAbortError = (error) =>
  error?.code === "ERR_CANCELED" || error?.name === "CanceledError" || error?.name === "AbortError";

export default function useHealth(pollMs = 10000, options = {}) {
  const { enabled = true } = options;
  const [status, setStatus] = useState(DEFAULT_STATUS);

  useEffect(() => {
    if (!enabled) {
      setStatus(DEFAULT_STATUS);
      return undefined;
    }

    let mounted = true;
    let timer;
    let controller;

    const fetchHealth = async () => {
      if (!mounted) return;
      if (controller) controller.abort();
      controller = new AbortController();

      try {
        const { data } = await client.get("/api/health", { signal: controller.signal });
        if (!mounted) return;
        setStatus({ ok: true, details: data, error: null });
      } catch (error) {
        if (!mounted || isAbortError(error)) return;
        const { userMessage } = extractErrorInfo(error, { fallbackMessage: "Сервис недоступен" });
        setStatus({ ok: false, details: null, error: userMessage });
      } finally {
        if (mounted) timer = setTimeout(fetchHealth, pollMs);
      }
    };

    fetchHealth();
    return () => {
      mounted = false;
      if (timer) clearTimeout(timer);
      if (controller) controller.abort();
    };
  }, [pollMs, enabled]);

  return status;
}
