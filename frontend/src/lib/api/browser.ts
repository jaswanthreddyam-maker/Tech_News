import { ApiTransport, RequestOptions } from "./transport";
import { sessionManager } from "@/lib/session/sessionManager";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

async function attemptTokenRefresh(): Promise<boolean> {
  const { useAppStore } = require("@/store/useStore");
  const state = useAppStore.getState();
  if (state.authRefreshSuppressUntil && state.authRefreshSuppressUntil > Date.now()) {

    return false;
  }

  try {
    const data = await sessionManager.refresh();
    if (data && data.user) {
      state.loginUser(data.user, data.access_token);
      return true;
    }
    return false;
  } catch (err: any) {

    state.setAuthRefreshSuppressUntil(Date.now() + 300000);
    return false;
  }
}

export class BrowserTransport implements ApiTransport {
  async fetch(endpoint: string, options: RequestOptions = {}): Promise<Response> {
    const { params, headers, timeoutMs = 10000, _isRetryAfterRefresh, ...restOptions } = options as any;
    
    let url = `${API_BASE_URL}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null) {
          searchParams.append(key, String(val));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    const requestHeaders = new Headers(headers);
    if (!requestHeaders.has("Content-Type") && !(restOptions.body instanceof FormData)) {
      requestHeaders.set("Content-Type", "application/json");
    }
    
    const correlationId = typeof crypto !== "undefined" ? crypto.randomUUID() : Math.random().toString(36).substring(7);
    requestHeaders.set("X-Correlation-ID", correlationId);

    const { useAppStore } = require("@/store/useStore");
    const token = sessionManager.getAccessToken() || useAppStore.getState().adminToken;
    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...restOptions,
        headers: requestHeaders,
        signal: controller.signal,
        credentials: "include",
      });

      clearTimeout(timeoutId);

      // Handle 401 Silent Refresh
      if (response.status === 401 && !_isRetryAfterRefresh && token) {
        const refreshed = await attemptTokenRefresh();
        if (refreshed) {
          // Retry the original request
          return this.fetch(endpoint, {
            ...options,
            _isRetryAfterRefresh: true,
          } as any);
        }
        const { useAppStore } = require("@/store/useStore");
        useAppStore.getState().logoutUser();
      }

      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      throw err; // Let the ApiClient handle network/timeout error retries
    }
  }
}
