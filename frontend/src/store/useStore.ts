import { create } from "zustand";
import type { Article } from "../services/api/news";
import { FeatureCapability } from "@/lib/auth/features";
import { sessionManager } from "@/lib/session/sessionManager";

import { clearUserQueryCache } from "@/lib/queryClient";

export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  permissions: string[];
}

export interface AuthGateModalState {
  isOpen: boolean;
  feature: FeatureCapability | null;
  returnUrl: string | null;
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

  // Auth Gate Modal State
  authGate: AuthGateModalState;
  openAuthGate: (feature: FeatureCapability, returnUrl?: string) => void;
  closeAuthGate: () => void;

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

  // Auth Gate Modal State
  authGate: {
    isOpen: false,
    feature: null,
    returnUrl: null,
  },
  openAuthGate: (feature: FeatureCapability, returnUrl?: string) =>
    set({
      authGate: {
        isOpen: true,
        feature,
        returnUrl: returnUrl || (typeof window !== "undefined" ? window.location.pathname + window.location.search : "/"),
      },
    }),
  closeAuthGate: () =>
    set({
      authGate: {
        isOpen: false,
        feature: null,
        returnUrl: null,
      },
    }),

  loginUser: (user, accessToken) => {
    sessionManager.setSession(accessToken);
    set({
      user,
      accessToken,
      isAdminAuthenticated: true,
      adminToken: accessToken,
      authGate: { isOpen: false, feature: null, returnUrl: null },
      authRefreshSuppressUntil: null,
    });
  },
  logoutUser: () => {
    sessionManager.clearSession();
    clearUserQueryCache();
    set({
      user: null,
      accessToken: null,
      isAdminAuthenticated: false,
      adminToken: null,
      authRefreshSuppressUntil: Date.now() + 300000, // suppress refresh storms for 5 min
    });
  },

  // Legacy admin token management — maps to user session for backward compat
  isAdminAuthenticated: false,
  adminToken: null,
  loginAdmin: (token) => {
    sessionManager.setSession(token);
    set({ isAdminAuthenticated: true, adminToken: token, accessToken: token });
  },
  logoutAdmin: () => {
    sessionManager.clearSession();
    clearUserQueryCache();
    set({
      isAdminAuthenticated: false,
      adminToken: null,
      accessToken: null,
      user: null,
    });
  },
}));
