import { API_BASE_URL } from "../config";

async function request(path, options = {}, authToken = "") {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
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

export function getCatalog(authToken) {
  return request("/catalog", { method: "GET" }, authToken);
}

export function getScheduleConfig(authToken) {
  return request("/schedule/config", { method: "GET" }, authToken);
}

export function putScheduleConfig(payload, authToken) {
  return request(
    "/schedule/config",
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
    authToken,
  );
}
