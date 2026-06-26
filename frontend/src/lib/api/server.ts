import { ApiTransport, RequestOptions } from "./transport";
import { randomUUID } from "crypto";

const API_BASE_URL = process.env.INTERNAL_API_URL || (process.env.API_PROXY_TARGET ? `${process.env.API_PROXY_TARGET}${process.env.NEXT_PUBLIC_API_URL || '/api/v1'}` : "http://localhost:8000/api/v1");

export class ServerTransport implements ApiTransport {
  async fetch(endpoint: string, options: RequestOptions = {}): Promise<Response> {
    const { params, headers, timeoutMs = 15000, tags, revalidate, ...restOptions } = options;
    
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
    
    const correlationId = randomUUID();
    requestHeaders.set("X-Correlation-ID", correlationId);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    // Apply Next.js fetch caching options
    const nextOpts: any = {};
    if (tags) {
      nextOpts.tags = tags;
    }
    if (revalidate !== undefined) {
      nextOpts.revalidate = revalidate;
    }

    try {
      const response = await fetch(url, {
        ...restOptions,
        cache: 'no-store',
        headers: requestHeaders,
        signal: controller.signal,
        next: Object.keys(nextOpts).length > 0 ? nextOpts : undefined,
      });

      clearTimeout(timeoutId);
      return response;
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }
}
