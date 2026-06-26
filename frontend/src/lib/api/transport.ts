export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
  timeoutMs?: number;
  tags?: string[];
  revalidate?: number | false;
}

export interface ApiTransport {
  fetch(url: string, options?: RequestOptions): Promise<Response>;
}
