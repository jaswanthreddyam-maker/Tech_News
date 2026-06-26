import { create } from "zustand";
import type { Article } from "../services/api/news";

export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  permissions: string[];
}

interface AppState {
  // Theme State
  theme: "dark" | "light";
  toggleTheme: () => void;

  // Navigation / Filter State
  selectedCategory: string | null;
  setCategory: (categorySlug: string | null) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  // Cached Articles State (prevents unnecessary refetching)
  cachedArticles: Article[];
  setCachedArticles: (articles: Article[] | ((prev: Article[]) => Article[])) => void;
  clearCache: () => void;

  // Authenticated User Session
  user: User | null;
  accessToken: string | null;
  loginUser: (user: User, accessToken: string) => void;
  logoutUser: () => void;
  isRestoringSession: boolean;
  setRestoringSession: (loading: boolean) => void;
  authRefreshSuppressUntil: number | null;
  setAuthRefreshSuppressUntil: (time: number | null) => void;

  // Administrative Authentication Session (backward compat)
  isAdminAuthenticated: boolean;
  adminToken: string | null;
  loginAdmin: (token: string) => void;
  logoutAdmin: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Defaults to sleek Dark Mode out-of-the-box
  theme: "dark",
  toggleTheme: () =>
    set((state) => {
      const nextTheme = state.theme === "dark" ? "light" : "dark";
      if (typeof window !== "undefined") {
        document.documentElement.classList.remove("dark", "light");
        document.documentElement.classList.add(nextTheme);
      }
      return { theme: nextTheme };
    }),

  selectedCategory: null,
  setCategory: (categorySlug) => set({ selectedCategory: categorySlug }),

  searchQuery: "",
  setSearchQuery: (query) => set({ searchQuery: query }),

  cachedArticles: [],
  setCachedArticles: (articles) =>
    set((state) => ({
      cachedArticles:
        typeof articles === "function" ? articles(state.cachedArticles) : articles,
    })),
  clearCache: () => set({ cachedArticles: [] }),

  // User session
  user: null,
  accessToken: null,
  isRestoringSession: true,
  setRestoringSession: (loading) => set({ isRestoringSession: loading }),
  authRefreshSuppressUntil: null,
  setAuthRefreshSuppressUntil: (time) => set({ authRefreshSuppressUntil: time }),
  loginUser: (user, accessToken) =>
    set({
      user,
      accessToken,
      isAdminAuthenticated: true,
      adminToken: accessToken,
    }),
  logoutUser: () =>
    set({
      user: null,
      accessToken: null,
      isAdminAuthenticated: false,
      adminToken: null,
    }),

  // Legacy admin token management — maps to user session for backward compat
  isAdminAuthenticated: false,
  adminToken: null,
  loginAdmin: (token) =>
    set({ isAdminAuthenticated: true, adminToken: token, accessToken: token }),
  logoutAdmin: () =>
    set({
      isAdminAuthenticated: false,
      adminToken: null,
      accessToken: null,
      user: null,
    }),
}));
