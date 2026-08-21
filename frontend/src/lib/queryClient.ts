import { QueryClient } from "@tanstack/react-query";

let browserQueryClient: QueryClient | null = null;

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 60 seconds
        gcTime: 5 * 60 * 1000, // 5 minutes
        retry: 2,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
      },
    },
  });
}

export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server: always create a fresh query client to avoid shared state across requests
    return makeQueryClient();
  }

  // Browser: maintain a single client instance
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

/**
 * Purges all user-scoped queries and caches upon user logout,
 * preventing cross-user data leakage in shared browser environments.
 */
export function clearUserQueryCache(): void {
  if (browserQueryClient) {
    browserQueryClient.clear();
  }
}
