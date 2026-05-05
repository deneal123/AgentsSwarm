const HTTP_URL_REGEX = /https?:\/\/[^\s"'<>()[\]{}]+/gi;
const DOMAIN_URL_REGEX = /\b(?:www\.)?[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+(?:\/[^\s"'<>()[\]{}]*)?/gi;

const TRAILING_PUNCTUATION_REGEX = /[),.;!?]+$/g;
const DOMAIN_SHAPE_REGEX = /^(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:\/.*)?$/i;

export function normalizeUrlCandidate(value) {
  const cleaned = String(value || '').trim().replace(TRAILING_PUNCTUATION_REGEX, '');
  if (!cleaned) {
    return '';
  }

  if (/^https?:\/\//i.test(cleaned)) {
    return cleaned;
  }

  // Ignore non-http schemes here; parser endpoint expects web URLs.
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(cleaned)) {
    return '';
  }

  if (DOMAIN_SHAPE_REGEX.test(cleaned)) {
    return `https://${cleaned}`;
  }

  return '';
}

export function extractUrlCandidates(text, max = 2) {
  const source = String(text || '');
  if (!source) {
    return [];
  }

  const urls = [];
  const seen = new Set();

  const pushCandidate = (candidate) => {
    const normalized = normalizeUrlCandidate(candidate);
    if (!normalized) {
      return;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    urls.push(normalized);
  };

  for (const match of source.match(HTTP_URL_REGEX) || []) {
    pushCandidate(match);
  }

  for (const match of source.match(DOMAIN_URL_REGEX) || []) {
    pushCandidate(match);
  }

  return urls.slice(0, max);
}
