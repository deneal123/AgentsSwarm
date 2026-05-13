import { useCallback, useState } from "react";
import { useAppToast } from "@shared/hooks/useAppToast";

export function useRecentThreads({ navigate, resolveSessionUserId, threadId, setMessages }) {
  const toast = useAppToast();
  const [recentThreads, setRecentThreads] = useState([]);
  const [deletingThreadId, setDeletingThreadId] = useState(null);

  const upsertRecentThread = useCallback((targetThreadId, titleCandidate) => {
    const tid = String(targetThreadId || "").trim();
    if (!tid) return;
    const nextTitle = (String(titleCandidate || "").trim() || `Чат ${tid.slice(0, 8)}`).slice(0, 72);

    setRecentThreads((prev) => {
      const normalized = Array.isArray(prev) ? prev : [];
      const existing = normalized.find((thread) => {
        const candidateId = thread?.thread_id || thread?.id || thread;
        return String(candidateId) === tid;
      });
      const nextItem = existing ? { ...existing, title: nextTitle } : { thread_id: tid, title: nextTitle };
      const rest = normalized.filter((thread) => {
        const candidateId = thread?.thread_id || thread?.id || thread;
        return String(candidateId) !== tid;
      });
      return [nextItem, ...rest].slice(0, 18);
    });
  }, []);

  const handleDeleteThread = useCallback(async (thread, event) => {
    event.preventDefault();
    event.stopPropagation();
    const targetThreadId = thread?.thread_id || thread?.id || thread;
    if (!targetThreadId || deletingThreadId === targetThreadId) return;

    setDeletingThreadId(targetThreadId);
    try {
      const { deleteChatThread } = await import("@api/chat");
      await deleteChatThread(targetThreadId, resolveSessionUserId() || null);

      setRecentThreads((prev) => prev.filter((candidate) => {
        const candidateId = candidate?.thread_id || candidate?.id || candidate;
        return candidateId !== targetThreadId;
      }));

      if (targetThreadId === threadId) {
        setMessages([]);
        navigate("/");
      }
    } catch {
      toast({ title: "Не удалось удалить чат", status: "error", duration: 2200 });
    } finally {
      setDeletingThreadId(null);
    }
  }, [deletingThreadId, navigate, resolveSessionUserId, setMessages, threadId, toast]); // toast is stable (useAppToast)

  return {
    recentThreads,
    setRecentThreads,
    deletingThreadId,
    upsertRecentThread,
    handleDeleteThread,
  };
}
