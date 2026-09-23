import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

const API_BASE_URL = getApiBaseUrl();

// Storage keys
const ACCESS_TOKEN_KEY = "access_token";
const TOKEN_EXPIRES_KEY = "token_expires_at";
const HAS_SESSION_KEY = "has_session";
const CACHED_USER_KEY = "cached_user";

// In-memory access token storage (hydrated from localStorage across page refreshes)
let accessToken: string | null = null;
let tokenExpiresAt: number | null = null;

// Default session expiration: 7 days (604800 seconds)
const DEFAULT_SESSION_EXPIRY = 7 * 86400;

export const sessionManager = {
  isAuthenticated(): boolean {
    if (!accessToken && typeof window !== "undefined") {
      try {
        const storedToken = localStorage.getItem(ACCESS_TOKEN_KEY) || sessionStorage.getItem(ACCESS_TOKEN_KEY);
        const storedExp = localStorage.getItem(TOKEN_EXPIRES_KEY) || sessionStorage.getItem(TOKEN_EXPIRES_KEY);
        if (storedToken && storedExp) {
          const exp = parseInt(storedExp, 10);
          if (Date.now() < exp - 10000) {
            accessToken = storedToken;
            tokenExpiresAt = exp;
          } else {
            this.clearSession();
          }
        }
      } catch {
        // Ignore storage access errors
      }
    }
    if (!accessToken || !tokenExpiresAt) return false;
    return Date.now() < tokenExpiresAt - 10000;
  },

  getAccessToken(): string | null {
    return this.isAuthenticated() ? accessToken : null;
  },

  getCachedUser(): any | null {
    if (typeof window === "undefined") return null;
    try {
      const userStr = localStorage.getItem(CACHED_USER_KEY);
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  },

  setSession(token: string, expiresInSeconds: number = DEFAULT_SESSION_EXPIRY) {
    accessToken = token;
    tokenExpiresAt = Date.now() + (expiresInSeconds * 1000);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
        localStorage.setItem(TOKEN_EXPIRES_KEY, String(tokenExpiresAt));
        sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
        sessionStorage.setItem(TOKEN_EXPIRES_KEY, String(tokenExpiresAt));
        localStorage.setItem(HAS_SESSION_KEY, "true");
        localStorage.setItem("session_event", `login_${Date.now()}`);
      } catch {
        // Ignore storage access errors
      }
    }
  },

  setCachedUser(user: any) {
    if (typeof window !== "undefined" && user) {
      try {
        localStorage.setItem(CACHED_USER_KEY, JSON.stringify(user));
        localStorage.setItem(HAS_SESSION_KEY, "true");
      } catch {
        // Ignore storage access errors
      }
    }
  },

  clearSession() {
    accessToken = null;
    tokenExpiresAt = null;
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(TOKEN_EXPIRES_KEY);
        sessionStorage.removeItem(ACCESS_TOKEN_KEY);
        sessionStorage.removeItem(TOKEN_EXPIRES_KEY);
        localStorage.removeItem(HAS_SESSION_KEY);
        localStorage.removeItem(CACHED_USER_KEY);
        localStorage.setItem("session_event", `logout_${Date.now()}`);
      } catch {
        // Ignore storage access errors
      }
    }
  },

  async login(credentials: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials)
    });
    
    if (!res.ok) throw new Error("Login failed");
    
    const payload = await res.json();
    const data = payload.data || payload;
    
    if (data.access_token) {
      const ttl = credentials.remember_me ? 28 * 86400 : DEFAULT_SESSION_EXPIRY;
      this.setSession(data.access_token, ttl);
      if (data.user) {
        this.setCachedUser(data.user);
      }
    }
    return data;
  },

  async register(details: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(details)
    });

    if (!res.ok) {
      const err: any = new Error("Registration failed");
      err.status = res.status;
      throw err;
    }

    const payload = await res.json();
    const data = payload.data || payload;

    if (data.access_token) {
      this.setSession(data.access_token, DEFAULT_SESSION_EXPIRY);
      if (data.user) {
        this.setCachedUser(data.user);
      }
    }
    return data;
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Ignore network errors on logout
    } finally {
      this.clearSession();
    }
  },

  async refresh(): Promise<any> {
    if (typeof window !== "undefined" && !localStorage.getItem(HAS_SESSION_KEY)) {
      return null;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        // ONLY clear session if our locally stored token is ALSO expired
        if ((res.status === 401 || res.status === 403) && !this.isAuthenticated()) {
          this.clearSession();
        }
        return null;
      }
      
      const payload = await res.json();
      const data = payload.data || payload;
      
      if (data.access_token) {
        this.setSession(data.access_token);
        if (data.user) {
          this.setCachedUser(data.user);
        }
        return data;
      }
      return null;
    } catch {
      clearTimeout(timeoutId);
      return null;
    }
  }
};
