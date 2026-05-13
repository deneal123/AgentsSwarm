import { useCallback, useReducer } from 'react';

const initialState = {
  taskId: null,
  instruction: null,
  status: 'idle', // idle | synthesizing | creating | running | completed | failed | canceled
  plan: [],
  events: [],
  images: [],
};

function reducer(state, action) {
  switch (action.type) {
    case 'RESET':
      return { ...initialState };

    case 'SET_SYNTHESIZING':
      return { ...state, status: 'synthesizing' };

    case 'SET_INSTRUCTION':
      return { ...state, instruction: action.instruction, status: 'creating' };

    case 'SET_TASK_CREATED':
      return { ...state, taskId: action.taskId, status: 'running' };

    case 'APPEND_EVENT': {
      const event = action.event;
      return {
        ...state,
        events: [...state.events, { ...event, id: `oe_${Date.now()}_${Math.random()}` }],
      };
    }

    case 'UPDATE_PLAN':
      return { ...state, plan: action.plan || [] };

    case 'APPEND_IMAGES': {
      const newImages = (action.images || []).map((img, i) => ({
        id: `img_${Date.now()}_${i}`,
        data: img,
        label: action.label || `Карта ${state.images.length + i + 1}`,
      }));
      return { ...state, images: [...state.images, ...newImages] };
    }

    case 'SET_STATUS':
      return { ...state, status: action.status };

    default:
      return state;
  }
}

export function useOrchestratorState() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);

  const handleOrchestratorAgentEvent = useCallback((event) => {
    const eventType = event?.metadata?.event_type;
    if (!eventType) return;

    switch (eventType) {
      case 'orchestrator_synthesizing':
        dispatch({ type: 'SET_SYNTHESIZING' });
        break;

      case 'orchestrator_instruction':
        dispatch({ type: 'SET_INSTRUCTION', instruction: event.metadata.instruction || event.data });
        break;

      case 'orchestrator_creating_task':
        // status already 'creating' from SET_INSTRUCTION
        break;

      case 'orchestrator_task_created':
        dispatch({ type: 'SET_TASK_CREATED', taskId: event.metadata.task_id });
        break;

      case 'orchestrator_event': {
        const orchEvent = event.metadata.orchestrator_event || {};
        dispatch({ type: 'APPEND_EVENT', event: orchEvent });

        // Extract plan updates from event meta if present
        const meta = orchEvent.meta || {};
        if (meta.plan && Array.isArray(meta.plan)) {
          dispatch({ type: 'UPDATE_PLAN', plan: meta.plan });
        }

        // Update status from task_status in event meta
        const taskStatus = meta.task_status || meta.state || '';
        if (taskStatus) {
          const normalized = taskStatus.toLowerCase();
          const terminalMap = { completed: 'completed', failed: 'failed', canceled: 'canceled' };
          if (terminalMap[normalized]) {
            dispatch({ type: 'SET_STATUS', status: terminalMap[normalized] });
          }
        }
        break;
      }

      case 'orchestrator_images': {
        const images = event.data?.images || [];
        if (images.length > 0) {
          dispatch({ type: 'APPEND_IMAGES', images, label: event.data?.label });
        }
        break;
      }

      default:
        break;
    }
  }, []);

  // Also handle structured_output with orchestrator_images
  const handleOrchestratorStructuredOutput = useCallback((event) => {
    if (event?.metadata?.event_type === 'orchestrator_images') {
      const images = event.data?.images || [];
      if (images.length > 0) {
        dispatch({ type: 'APPEND_IMAGES', images, label: event.data?.label });
      }
    }
  }, []);

  const isActive = state.status !== 'idle';

  return {
    state,
    isActive,
    actions: {
      reset,
      handleOrchestratorAgentEvent,
      handleOrchestratorStructuredOutput,
    },
  };
}
