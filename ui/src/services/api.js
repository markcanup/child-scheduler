import { API_BASE_URL } from "../config";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    const message = data?.error?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return data;
}

export function getCatalog() {
  return request("/catalog", { method: "GET" });
}

export function getScheduleConfig() {
  return request("/schedule/config", { method: "GET" });
}

export function putScheduleConfig(payload) {
  return request("/schedule/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
