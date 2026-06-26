export function normalizeNotifications(payload: any): any[] {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === "object") {
    if (Array.isArray(payload.notifications)) return payload.notifications;
    if (Array.isArray(payload.data)) return payload.data;
  }
  return [];
}

export function normalizeAiJobs(payload: any): any[] {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === "object") {
    if (Array.isArray(payload.jobs)) return payload.jobs;
    if (Array.isArray(payload.data)) return payload.data;
  }
  return [];
}

export function normalizeAiCosts(payload: any): any {
  let base = payload;
  if (payload && payload.data && typeof payload.data === "object") {
    base = payload.data;
  }
  return {
    ...base,
    models_breakdown: Array.isArray(base?.models_breakdown) ? base.models_breakdown : []
  };
}

export function normalizeArticles(payload: any): any[] {
  let results = [];
  if (Array.isArray(payload)) {
    results = payload;
  } else if (payload && typeof payload === "object") {
    if (Array.isArray(payload.articles)) results = payload.articles;
    else if (Array.isArray(payload.data)) results = payload.data;
  }
  
  return results.map((r: any) => ({
    id: r.id,
    title: r.title,
    slug: r.slug || r.url || "",
    summary: r.summary || "",
    content: r.content || "",
    source: r.source || "System",
    category: r.tags && r.tags.length > 0 ? r.tags[0] : (r.type === "processed" ? "Processed" : "Raw Ingest"),
    published_at: r.published_at || new Date().toISOString(),
    ...r
  }));
}
