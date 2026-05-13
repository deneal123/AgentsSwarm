import { useCallback, useReducer } from 'react';

const initialState = {
  taskId: null,
  instruction: null,
  reasoning: null,
  status: 'idle', // idle | synthesizing | creating | running | completed | failed | canceled
  plan: [],
  events: [],
  images: [],
};

// Normalize any image variant into {id, src, label, isBest}
function normalizeImages(data, existingCount) {
  const results = [];

  // Case 1: single map_image  → data.image_b64
  if (data.image_b64) {
    const b64 = data.image_b64;
    results.push({
      id: `img_${Date.now()}_0`,
      src: b64.startsWith('data:') ? b64 : `data:${data.mime || 'image/png'};base64,${b64}`,
      label: data.label || `Карта ${existingCount + 1}`,
      isBest: false,
    });
  }

  // Case 2: route_images array → data.images
  if (Array.isArray(data.images)) {
    data.images.forEach((img, i) => {
      if (!img.image_b64) return;
      const b64 = img.image_b64;
      results.push({
        id: `img_${Date.now()}_${i}`,
        src: b64.startsWith('data:') ? b64 : `data:${img.mime || 'image/png'};base64,${b64}`,
        label: img.name ? `Маршрут: ${img.name}${img.is_best ? ' ★' : ''}` : `Карта ${existingCount + i + 1}`,
        isBest: img.is_best || false,
      });
    });
  }

  return results;
}

function reducer(state, action) {
  switch (action.type) {
    case 'RESET':
      return { ...initialState };

    case 'SET_SYNTHESIZING':
      return { ...state, status: 'synthesizing' };

    case 'SET_REASONING':
      return { ...state, reasoning: action.reasoning };

    case 'SET_INSTRUCTION':
      return { ...state, instruction: action.instruction, status: 'creating' };

    case 'SET_TASK_CREATED':
      return { ...state, taskId: action.taskId, status: 'running' };

    case 'UPDATE_PLAN':
      return { ...state, plan: action.plan || [] };

    case 'APPEND_EVENT': {
      const ev = action.event;
      if (!ev.message) return state;
      return {
        ...state,
        events: [...state.events, { ...ev, _id: `oe_${Date.now()}_${Math.random()}` }],
      };
    }

    case 'APPEND_IMAGES': {
      const newImages = normalizeImages(action.data, state.images.length);
      if (newImages.length === 0) return state;
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

      case 'orchestrator_reasoning':
        dispatch({
          type: 'SET_REASONING',
          reasoning: event.metadata?.reasoning || (typeof event.data === 'string' ? event.data : null),
        });
        break;

      case 'orchestrator_instruction':
        dispatch({
          type: 'SET_INSTRUCTION',
          instruction: event.metadata?.instruction || (typeof event.data === 'string' ? event.data : null),
        });
        break;

      case 'orchestrator_creating_task':
        break;

      case 'orchestrator_task_created':
        dispatch({ type: 'SET_TASK_CREATED', taskId: event.metadata?.task_id });
        break;

      case 'orchestrator_plan':
        if (Array.isArray(event.metadata?.plan)) {
          dispatch({ type: 'UPDATE_PLAN', plan: event.metadata.plan });
        }
        break;

      case 'orchestrator_event': {
        const orchEvent = event.metadata?.orchestrator_event || {};

        // Append to live event timeline
        dispatch({ type: 'APPEND_EVENT', event: orchEvent });

        // Update task status from orchestrator meta
        const meta = orchEvent.meta || {};
        const taskStatus = (meta.task_status || meta.state || '').toLowerCase();
        const terminalMap = { completed: 'completed', failed: 'failed', canceled: 'canceled' };
        if (terminalMap[taskStatus]) {
          dispatch({ type: 'SET_STATUS', status: terminalMap[taskStatus] });
        }
        break;
      }

      // STRUCTURED_OUTPUT events arrive here when event.type === 'structured_output'
      // and metadata.event_type === 'orchestrator_images'
      case 'orchestrator_images': {
        const data = event.data || {};
        dispatch({ type: 'APPEND_IMAGES', data });
        break;
      }

      default:
        break;
    }
  }, []);

  const isActive = state.status !== 'idle';

  return {
    state,
    isActive,
    actions: {
      reset,
      handleOrchestratorAgentEvent,
    },
  };
}
