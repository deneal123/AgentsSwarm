const NON_EMPTY_STRING_TYPES = ['string'];

const isObject = (value) => typeof value === 'object' && value !== null && !Array.isArray(value);

const isNonEmptyString = (value) => NON_EMPTY_STRING_TYPES.includes(typeof value) && value.trim().length > 0;

const baseEnvelopeValidator = (event) => {
  if (!isObject(event)) {
    return 'event payload must be an object';
  }

  const eventType = event.type || event.event;
  if (!isNonEmptyString(eventType)) {
    return 'event type must be a non-empty string';
  }

  if (!isNonEmptyString(event.job_id)) {
    return 'job_id must be a non-empty string';
  }

  if (!isNonEmptyString(event.thread_id)) {
    return 'thread_id must be a non-empty string';
  }

  if (event.metadata !== undefined && !isObject(event.metadata)) {
    return 'metadata must be an object when provided';
  }

  return null;
};

const validatorsByType = {
  job_created: (event) => {
    if (!isObject(event.data)) {
      return 'data must be an object for job_created';
    }
    return null;
  },
  stream_chunk: (event) => {
    if (typeof event.data !== 'string') {
      return 'data must be a string for stream_chunk';
    }
    return null;
  },
  error: (event) => {
    if (!isObject(event.data)) {
      return 'data must be an object for error';
    }
    if (!isNonEmptyString(event.data.message)) {
      return 'data.message must be a non-empty string for error';
    }
    return null;
  },
  complete: (event) => {
    if (!isObject(event.data)) {
      return 'data must be an object for complete';
    }
    return null;
  },
};

export const validateChatEvent = (event) => {
  if (!isObject(event)) {
    return { isValid: false, error: 'event payload must be an object', eventType: null };
  }

  const eventType = event.type || event.event;
  const typeValidator = validatorsByType[eventType];

  if (!typeValidator) {
    return { isValid: true, error: null, eventType: isNonEmptyString(eventType) ? eventType : null };
  }

  const baseError = baseEnvelopeValidator(event);
  if (baseError) {
    return { isValid: false, error: baseError, eventType };
  }

  const specificError = typeValidator(event);
  if (specificError) {
    return { isValid: false, error: specificError, eventType };
  }

  return { isValid: true, error: null, eventType };
};
