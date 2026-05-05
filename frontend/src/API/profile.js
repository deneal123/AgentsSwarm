import client from "./client";

export async function fetchProfile({ signal } = {}) {
  const response = await client.get("/api/profile/me", { signal });
  return response.data;
}

export async function updateProfile(payload, { signal } = {}) {
  const response = await client.patch("/api/profile/me", payload, { signal });
  return response.data;
}

export async function getQuotaPlans({ signal } = {}) {
  const response = await client.get("/api/billing/quotas/preview", { signal });
  return response.data;
}

export async function getUserQuota({ signal } = {}) {
  const response = await client.get("/api/billing/quota", { signal });
  return response.data;
}
