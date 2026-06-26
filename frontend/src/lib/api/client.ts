import { ApiTransport, RequestOptions } from "./transport";
import { BrowserTransport } from "./browser";
import { ServerTransport } from "./server";
import { ApiError, NetworkError, TimeoutError } from "./errors";

export class ApiClient {
  private transport: ApiTransport;

  constructor() {
    if (typeof window !== "undefined") {
      this.transport = new BrowserTransport();
    } else {
      this.transport = new ServerTransport();
    }
  }
  async fetchRaw(endpoint: string, options: RequestOptions = {}): Promise<Response> {
    const isGet = !options.method || options.method.toUpperCase() === "GET";
    const maxRetries = isGet ? 2 : 0;
    let attempt = 0;
    
    while (attempt <= maxRetries) {
      const startTime = performance.now();
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || 10000);
      
      const fetchOptions = {
        ...options,
        signal: controller.signal,
      };

      try {
        const response = await this.transport.fetch(endpoint, fetchOptions);
        clearTimeout(timeoutId);
        const duration = Math.round(performance.now() - startTime);
        
        // Expose Correlation IDs and caching metadata on development
        if (process.env.NODE_ENV !== "production") {
          const cid = response.headers.get("x-correlation-id") || options.headers?.["X-Correlation-ID" as keyof typeof options.headers] || "N/A";
          const cacheStatus = response.headers.get("x-nextjs-cache") || "MISS";
          // eslint-disable-next-line no-console

        }

        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          const errorMessage = payload?.error?.message || payload?.detail || response.statusText || "Request failed";
          throw new ApiError(
            errorMessage,
            response.status,
            payload?.error?.code || "HTTP_ERROR",
            payload?.correlation_id
          );
        }

        return response;
      } catch (err: any) {
        clearTimeout(timeoutId);
        const duration = Math.round(performance.now() - startTime);
        attempt++;
        
        const isTimeout = err.name === "AbortError";
        const isNetworkError = err instanceof TypeError;
        
        if (process.env.NODE_ENV !== "production") {
          // eslint-disable-next-line no-console

        }

        if (err instanceof ApiError) {
          throw err;
        }

        if (attempt > maxRetries) {
          if (isTimeout) {
            throw new TimeoutError(`Request timed out after ${options.timeoutMs || 10000}ms.`);
          }
          if (isNetworkError) {
            throw new NetworkError("API Gateway connection offline or network dropped.");
          }
          throw err;
        }

        const backoffDelay = 150 * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, backoffDelay));
      }
    }
    
    throw new Error("Network request failed after multiple attempts.");
  }

  async fetchJson<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const response = await this.fetchRaw(endpoint, options);
    const payload = await response.json();
    return payload as T;
  }
}

export const apiClient = new ApiClient();

// Backwards compatibility shim for existing codebase
export async function apiFetch<T>(endpoint: string, options?: any): Promise<T> {
  const payload = await apiClient.fetchJson<any>(endpoint, options);
  
  // Backwards compatibility unwrapper (we will migrate endpoints off this to use schemas)
  if (
    payload &&
    typeof payload === "object" &&
    "status" in payload &&
    "correlation_id" in payload &&
    "data" in payload &&
    !("pagination" in payload) &&
    (payload.status === "success" || payload.status === "error")
  ) {
    return payload.data as T;
  }
  
  return payload as T;
}
