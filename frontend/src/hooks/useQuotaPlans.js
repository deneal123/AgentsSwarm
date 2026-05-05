import { useCallback, useEffect, useRef, useState } from "react";
import { getQuotaPlans } from "@api";
import extractErrorInfo from "@utils/errorHandler";
import isAbortError from "@utils/isAbortError";

export default function useQuotaPlans(autoLoad = false) {
  const [plans, setPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(Boolean(autoLoad));
  const [error, setError] = useState(null);

  const abortRef = useRef(null);
  const isMountedRef = useRef(false);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  const loadPlans = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    try {
      const response = await getQuotaPlans({ signal: controller.signal });
      if (!isMountedRef.current || controller.signal.aborted) {
        return null;
      }
      setPlans(response);
      return response;
    } catch (err) {
      if (isAbortError(err) || controller.signal.aborted) {
        return null;
      }
      const { userMessage } = extractErrorInfo(err, {
        fallbackMessage: "Не удалось загрузить тарифы",
      });
      setError(userMessage);
      throw err;
    } finally {
      if (!isMountedRef.current || controller.signal.aborted) {
        return;
      }
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (autoLoad) {
      loadPlans().catch(() => {});
    }
  }, [autoLoad, loadPlans]);

  return { plans, isLoading, error, loadPlans };
}
