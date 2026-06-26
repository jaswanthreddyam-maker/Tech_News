const SEARCH_HISTORY_KEY = "tech_news_search_history";
const MAX_HISTORY = 10;

export function getSearchHistory(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(SEARCH_HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    // eslint-disable-next-line no-console

    return [];
  }
}

export function saveSearchHistory(query: string) {
  if (typeof window === "undefined" || !query.trim()) return;
  const q = query.trim();
  
  const history = getSearchHistory();
  const updated = [q, ...history.filter(item => item.toLowerCase() !== q.toLowerCase())].slice(0, MAX_HISTORY);
  
  try {
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(updated));
  } catch (e) {
    // eslint-disable-next-line no-console

  }
}

export function clearSearchHistory() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SEARCH_HISTORY_KEY);
}
