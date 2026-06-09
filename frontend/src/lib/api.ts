/**
 * Centralized API client.
 *
 * Injects the auth token from localStorage on every request.
 * Handles 401 by clearing the session and redirecting to /login.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "stocker_token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/** Auth endpoints own their own 401 semantics (bad credentials), so the global
 *  "session expired → redirect" handler must not hijack them. */
function isAuthPath(path: string): boolean {
  return path.startsWith("/v1/auth/");
}

async function handleResponse(res: Response, path: string) {
  // A 401 on a non-auth call means the session token is missing/expired —
  // clear it and bounce to login. A 401 on an auth call (e.g. wrong password)
  // must fall through so the page can surface the server's message.
  if (res.status === 401 && !isAuthPath(path)) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: authHeaders(),
  });
  return handleResponse(res, path);
}

export async function apiPost(path: string, body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse(res, path);
}

export async function apiDelete(path: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleResponse(res, path);
}

/** SSE helper — returns raw EventSource (auth token passed as query param) */
export function createEventSource(path: string): EventSource {
  return new EventSource(`${API_BASE}${path}`);
}

export { API_BASE, TOKEN_KEY };
