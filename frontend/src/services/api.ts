import { useAppStore } from "../store/useStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const DEFAULT_TIMEOUT_MS = 10000; // 10s fetch timeout policy

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
  timeoutMs?: number;
  _isRetryAfterRefresh?: boolean;
}

export class APIClientError extends Error {
  status: number;
  code: string;
  
  constructor(message: string, status: number, code: string = "API_ERROR") {
    super(message);
    this.name = "APIClientError";
    this.status = status;
    this.code = code;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const state = useAppStore.getState();
    if (state.authRefreshSuppressUntil && state.authRefreshSuppressUntil > Date.now()) {

      return false;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {

      controller.abort();
    }, 5000);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          state.setAuthRefreshSuppressUntil(Date.now() + 300000);
        }
        return false;
      }

      const payload = await response.json();
      const data = payload.data || payload;

      if (data.access_token && data.user) {
        state.loginUser(data.user, data.access_token);
        return true;
      }
      return false;
    } catch (err: any) {
      clearTimeout(timeoutId);

      state.setAuthRefreshSuppressUntil(Date.now() + 300000);
      return false;
    }
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, timeoutMs = DEFAULT_TIMEOUT_MS, _isRetryAfterRefresh, ...restOptions } = options;
  
  // 1. Construct URL with query parameters
  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, val);
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // 2. Prepare headers with Correlation ID & Authorization
  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has("Content-Type") && !(restOptions.body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }
  
  // Inject Correlation ID for telemetry trace tracking
  const correlationId = typeof crypto !== "undefined" ? crypto.randomUUID() : Math.random().toString(36).substring(7);
  requestHeaders.set("X-Correlation-ID", correlationId);

  // Inject Authorization Token — prefer accessToken, fallback to adminToken for backward compat
  const state = useAppStore.getState();
  const token = state.accessToken || state.adminToken;
  if (token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  // 3. Execution with dynamic exponential retry support on connection drops
  const maxRetries = 3;
  let attempt = 0;
  
  while (attempt <= maxRetries) {
    // Implement explicit request timeouts using AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...restOptions,
        headers: requestHeaders,
        signal: controller.signal,
        credentials: "include",
      });

      // Clear the safety timeout
      clearTimeout(timeoutId);

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        const apiError = new APIClientError(
          payload?.error?.message || payload?.detail || response.statusText || "Request failed",
          response.status,
          payload?.error?.code || "HTTP_ERROR"
        );

        // Silent 401 refresh interceptor: attempt token refresh once
        // Only attempt refresh if the original request had an auth token
        // (prevents cascading failures for unauthenticated guest requests)
        if (response.status === 401 && !_isRetryAfterRefresh && token) {
          const refreshed = await attemptTokenRefresh();
          if (refreshed) {
            // Retry the original request with the new token
            return apiFetch<T>(endpoint, {
              ...options,
              _isRetryAfterRefresh: true,
            });
          }
          // Refresh failed — log out user and throw
          useAppStore.getState().logoutUser();
        }

        throw apiError;
      }

      // Return unified success data wrapper — handle both { data: ... } and raw payloads
      return (payload.data !== undefined ? payload.data : payload) as T;
      
    } catch (err: any) {
      clearTimeout(timeoutId);
      attempt++;
      
      const isTimeout = err.name === "AbortError";
      const isNetworkError = err instanceof TypeError; // typical fetch failure
      
      // If it's a structural API error (e.g. 4xx/5xx status code), fail-fast immediately
      if (err instanceof APIClientError) {
        throw err;
      }

      if (attempt > maxRetries) {
        if (isTimeout) {

          throw new APIClientError(`Request timed out after ${timeoutMs}ms.`, 408, "TIMEOUT_ERROR");
        }
        if (isNetworkError) {

          throw new APIClientError("API Gateway connection offline or network dropped.", 503, "NETWORK_ERROR");
        }
        throw err;
      }

      // Wait before retrying (Exponential Backoff: 300ms, 600ms, 1200ms)
      const backoffDelay = 150 * Math.pow(2, attempt);
      await new Promise((resolve) => setTimeout(resolve, backoffDelay));
    }
  }
  
  throw new Error("Network request failed after multiple attempts.");
}
