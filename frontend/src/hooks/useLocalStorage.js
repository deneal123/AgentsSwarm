import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Simple localStorage-backed state hook.
 * @param {string} key
 * @param {any} defaultValue
 */
export default function useLocalStorage(key, defaultValue) {
  const defaultRef = useRef(defaultValue);
  const isBrowser = typeof window !== "undefined" && typeof window.localStorage !== "undefined";

  const readStoredValue = useCallback(() => {
    if (!isBrowser) {
      return typeof defaultRef.current === "function" ? defaultRef.current() : defaultRef.current;
    }

    try {
      const stored = window.localStorage.getItem(key);
      if (stored === null) {
        return typeof defaultRef.current === "function" ? defaultRef.current() : defaultRef.current;
      }
      return JSON.parse(stored);
    } catch {
      return typeof defaultRef.current === "function" ? defaultRef.current() : defaultRef.current;
    }
  }, [isBrowser, key]);

  const [value, setValue] = useState(readStoredValue);

  useEffect(() => {
    if (!isBrowser) {
      return undefined;
    }

    try {
      if (value === undefined) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, JSON.stringify(value));
      }
    } catch {
      // no-op
    }

    return undefined;
  }, [isBrowser, key, value]);

  useEffect(() => {
    if (!isBrowser) {
      return undefined;
    }

    setValue(readStoredValue());
    return undefined;
  }, [isBrowser, key, readStoredValue]);

  return [value, setValue];
}
