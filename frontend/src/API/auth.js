import client from "./client";

export async function login(payload) {
  const response = await client.post("/api/auth/v1/login", payload);
  return response.data;
}

export async function registerUser(payload) {
  const response = await client.post("/api/auth/v1/register", payload);
  return response.data;
}

export function logoutLocal() {
  document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
}
