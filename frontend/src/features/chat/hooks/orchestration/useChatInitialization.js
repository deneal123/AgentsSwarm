import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { createThreadId } from '../../utils/chatThread';

export function useChatInitialization(routeThreadId) {
  const [fallbackThreadId] = useState(() => createThreadId());
  const [searchParams] = useSearchParams();
  const [selectedModelOverride, setSelectedModelOverride] = useState(() => searchParams.get('model') || '');

  const params = useMemo(() => ({
    initialMessage: searchParams.get('initial'),
    initialManualModel: searchParams.get('model') || '',
    initialInputType: searchParams.get('input_type') || '',
    initialWebSearch: searchParams.get('web_search') === 'true',
    initialDeepResearch: searchParams.get('deep_research') === 'true',
    initialFileContext: searchParams.get('file_context') || '',
  }), [searchParams]);

  return {
    state: {
      threadId: routeThreadId || fallbackThreadId,
      selectedModelOverride,
      ...params,
    },
    actions: {
      setSelectedModelOverride,
    },
  };
}
