import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchProfile, updateProfile } from "@api";
import extractErrorInfo from "@utils/errorHandler";
import isAbortError from "@utils/isAbortError";

export default function useProfile(autoLoad = true) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(Boolean(autoLoad));
  const [isSaving, setIsSaving] = useState(false);
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

  const loadProfile = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    try {
      const profile = await fetchProfile({ signal: controller.signal });
      if (!isMountedRef.current || controller.signal.aborted) {
        return null;
      }
      setData(profile);
      return profile;
    } catch (err) {
      if (isAbortError(err) || controller.signal.aborted) {
        return null;
      }
      const { userMessage } = extractErrorInfo(err, {
        fallbackMessage: "Не удалось загрузить профиль",
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

  const saveProfile = useCallback(async (payload) => {
    setIsSaving(true);
    try {
      const updated = await updateProfile(payload);
      setData(updated);
      return updated;
    } catch (err) {
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  useEffect(() => {
    if (autoLoad) {
      loadProfile().catch(() => {});
    }
  }, [autoLoad, loadProfile]);

  const derived = useMemo(() => {
    if (!data) return { profile: null, quota: null };
    const { quota, ...profile } = data;
    return { profile, quota };
  }, [data]);

  return {
    data,
    profile: derived.profile,
    quota: derived.quota,
    isLoading,
    isSaving,
    error,
    refresh: loadProfile,
    update: saveProfile,
  };
}
