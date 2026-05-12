import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDisclosure } from '@chakra-ui/react';

export function useProfileData({ isAuthenticated, user }) {
  const disclosure = useDisclosure();
  const [profileData, setProfileData] = useState(null);
  const [profileMemoryCount, setProfileMemoryCount] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const userId = useMemo(() => {
    const id = user?.id;
    return id ? String(id) : '';
  }, [user?.id]);

  const resolveUserId = useCallback(() => {
    if (userId) {
      if (typeof window !== 'undefined') window.sessionStorage.setItem('user_id', userId);
      return userId;
    }
    const fromStorage = typeof window !== 'undefined' ? window.sessionStorage.getItem('user_id') : '';
    if (fromStorage) return fromStorage;
    if (typeof document !== 'undefined') {
      return document.cookie.split('; ').find((r) => r.startsWith('user_id='))?.split('=')[1] || '';
    }
    return '';
  }, [userId]);

  useEffect(() => {
    if (!isAuthenticated || !disclosure.isOpen) return;
    let cancelled = false;
    setIsLoading(true);
    (async () => {
      try {
        const { fetchProfile } = await import('@api/profile');
        const { getUserMemory } = await import('@api/chat');
        const prof = await fetchProfile().catch(() => null);
        if (cancelled) return;
        setProfileData(prof);
        const effectiveUserId = String(prof?.id || resolveUserId() || '').trim();
        if (effectiveUserId) {
          const memoryPayload = await getUserMemory(effectiveUserId).catch(() => null);
          if (!cancelled) {
            setProfileMemoryCount(Array.isArray(memoryPayload?.facts) ? memoryPayload.facts.length : 0);
          }
        } else if (!cancelled) {
          setProfileMemoryCount(0);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isAuthenticated, disclosure.isOpen, resolveUserId]);

  return {
    disclosure,
    profileData,
    profileMemoryCount,
    setProfileMemoryCount,
    isLoading,
    resolveUserId,
  };
}
