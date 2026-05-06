import { useCallback, useEffect, useMemo, useState } from "react";
import { useDisclosure } from "@chakra-ui/react";

export function useProfileDrawer({ isAuthenticated, user }) {
  const profileDisclosure = useDisclosure();
  const [profileData, setProfileData] = useState(null);
  const [profileQuota, setProfileQuota] = useState(null);
  const [profileMemoryCount, setProfileMemoryCount] = useState(null);
  const [isProfileLoading, setIsProfileLoading] = useState(false);

  const authenticatedUserId = useMemo(() => {
    const candidate = user?.id;
    return candidate ? String(candidate) : "";
  }, [user?.id]);

  const resolveSessionUserId = useCallback(() => {
    if (authenticatedUserId) {
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem("user_id", authenticatedUserId);
      }
      return authenticatedUserId;
    }
    const fromStorage = typeof window !== "undefined" ? window.sessionStorage.getItem("user_id") : "";
    if (fromStorage) {
      return fromStorage;
    }
    if (typeof document !== "undefined") {
      return document.cookie.split("; ").find((r) => r.startsWith("user_id="))?.split("=")[1] || "";
    }
    return "";
  }, [authenticatedUserId]);

  useEffect(() => {
    if (!isAuthenticated || !profileDisclosure.isOpen) return;
    let cancelled = false;
    setIsProfileLoading(true);
    (async () => {
      try {
        const { fetchProfile, getUserQuota } = await import("@api/profile");
        const { getUserMemory } = await import("@api/chat");
        const [prof, quota] = await Promise.all([fetchProfile().catch(() => null), getUserQuota().catch(() => null)]);
        if (cancelled) return;
        setProfileData(prof);
        setProfileQuota(quota);

        const effectiveUserId = String(prof?.id || resolveSessionUserId() || "").trim();
        if (effectiveUserId) {
          const memoryPayload = await getUserMemory(effectiveUserId).catch(() => null);
          if (!cancelled) {
            const count = Array.isArray(memoryPayload?.facts) ? memoryPayload.facts.length : 0;
            setProfileMemoryCount(count);
          }
        } else if (!cancelled) {
          setProfileMemoryCount(0);
        }
      } finally {
        if (!cancelled) setIsProfileLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, profileDisclosure.isOpen, resolveSessionUserId]);

  return {
    profileDisclosure,
    profileData,
    profileQuota,
    profileMemoryCount,
    isProfileLoading,
    resolveSessionUserId,
  };
}
