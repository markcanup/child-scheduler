import { API_BASE_URL } from "../config";

export class ApiRequestError extends Error {
  constructor(message, diagnostics) {
    super(message);
    this.name = "ApiRequestError";
    this.diagnostics = diagnostics;
  }
}

function buildRequestUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return null;
    }
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
}

function isExpiredJwt(token) {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp || !Number.isFinite(payload.exp)) {
    return false;
  }
  return Date.now() >= payload.exp * 1000;
}

async function request(path, options = {}, authToken = "") {
  const method = options.method || "GET";
  const url = buildRequestUrl(path);
  const requestStartedAt = new Date().toISOString();
  const headers = {
    "Content-Type": "application/json",
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(url, {
      headers,
      ...options,
    });
  } catch (error) {
    const diagnostics = {
      type: "network_error",
      request: {
        method,
        url,
        startedAt: requestStartedAt,
        hasAuthToken: Boolean(authToken),
        online: navigator.onLine,
      },
      runtime: {
        userAgent: navigator.userAgent,
      },
      error: {
        name: error?.name || "Error",
        message: error?.message || "Unknown fetch error",
      },
    };
    throw new ApiRequestError(`Failed to fetch ${path}.`, diagnostics);
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    let message = data?.error?.message || `Request failed (${response.status})`;
    if (response.status === 401 && authToken && isExpiredJwt(authToken)) {
      message = "Your sign-in token is expired. Sign in again and retry.";
    }
    const diagnostics = {
      type: "http_error",
      request: {
        method,
        url,
        startedAt: requestStartedAt,
        hasAuthToken: Boolean(authToken),
      },
      response: {
        status: response.status,
        statusText: response.statusText,
        contentType: response.headers.get("content-type") || "",
        body: data,
      },
    };
    throw new ApiRequestError(message, diagnostics);
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
