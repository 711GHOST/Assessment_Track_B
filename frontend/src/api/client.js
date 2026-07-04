// Central API client: token storage, automatic refresh on 401, error
// normalization. All components go through this module.

const BASE_URL = import.meta.env.VITE_API_URL || "";

const ACCESS_KEY = "rag.access";
const REFRESH_KEY = "rag.refresh";

export function getTokens() {
  return {
    access: localStorage.getItem(ACCESS_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  };
}

export function setTokens({ access_token, refresh_token }) {
  localStorage.setItem(ACCESS_KEY, access_token);
  localStorage.setItem(REFRESH_KEY, refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function normalizeDetail(detail) {
  if (!detail) return "Request failed. Is the backend running?";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
  }
  return JSON.stringify(detail);
}

async function refreshTokens() {
  const { refresh } = getTokens();
  if (!refresh) return false;
  try {
    const response = await fetch(`${BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!response.ok) return false;
    setTokens(await response.json());
    return true;
  } catch {
    return false;
  }
}

export async function api(path, { method = "GET", body, auth = true, _retry = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const { access } = getTokens();
  if (auth && access) headers.Authorization = `Bearer ${access}`;

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection.", 0);
  }

  if (response.status === 401 && auth && _retry) {
    if (await refreshTokens()) {
      return api(path, { method, body, auth, _retry: false });
    }
    clearTokens();
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(normalizeDetail(data?.detail), response.status);
  }
  return data;
}
