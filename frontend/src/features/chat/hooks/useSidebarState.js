import { useEffect, useMemo, useState } from 'react';
import { SIDEBAR_COLLAPSE_STORAGE_KEY } from '../constants/localStorageKeys';

export function useSidebarState({ recentThreads = [] }) {
  const [sidebarSearch, setSidebarSearch] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.localStorage.getItem(SIDEBAR_COLLAPSE_STORAGE_KEY) === '1';
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(SIDEBAR_COLLAPSE_STORAGE_KEY, isSidebarCollapsed ? '1' : '0');
  }, [isSidebarCollapsed]);

  const filteredRecentThreads = useMemo(() => {
    return recentThreads.filter((thread) => {
      if (!sidebarSearch.trim()) return true;
      const label = thread.title || thread.last_message || '';
      return label.toLowerCase().includes(sidebarSearch.toLowerCase());
    });
  }, [recentThreads, sidebarSearch]);

  return {
    sidebarSearch,
    setSidebarSearch,
    isSidebarCollapsed,
    setIsSidebarCollapsed,
    filteredRecentThreads,
  };
}
