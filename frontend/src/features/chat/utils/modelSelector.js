export const AUTO_MODE_LABEL = "Автоматический режим (Auto)";

export const normalizeModelList = (models) => {
  if (!Array.isArray(models)) return [];
  const unique = new Set();
  const result = [];

  for (const value of models) {
    const model = String(value || "").trim();
    if (!model || unique.has(model)) continue;
    unique.add(model);
    result.push(model);
  }

  return result;
};

export const resolveModelTriggerLabel = (selectedModel) => {
  return selectedModel ? String(selectedModel).trim() || AUTO_MODE_LABEL : AUTO_MODE_LABEL;
};
