import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

const API_BASE_URL = getApiBaseUrl();

// In-memory access token storage (hydrated from sessionStorage across F5 page refreshes)
let accessToken: string | null = null;
let tokenExpiresAt: number | null = null;

export const sessionManager = {
  isAuthenticated(): boolean {
    if (!accessToken && typeof window !== "undefined") {
      try {
        const storedToken = sessionStorage.getItem("access_token");
        const storedExp = sessionStorage.getItem("token_expires_at");
        if (storedToken && storedExp) {
          const exp = parseInt(storedExp, 10);
          if (Date.now() < exp - 10000) {
            accessToken = storedToken;
            tokenExpiresAt = exp;
          } else {
            sessionStorage.removeItem("access_token");
            sessionStorage.removeItem("token_expires_at");
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

  setSession(token: string, expiresInSeconds: number = 900) {
    accessToken = token;
    tokenExpiresAt = Date.now() + (expiresInSeconds * 1000);
    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem("access_token", token);
        sessionStorage.setItem("token_expires_at", String(tokenExpiresAt));
        localStorage.setItem("has_session", "true");
        localStorage.setItem("session_event", `login_${Date.now()}`);
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
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("token_expires_at");
        localStorage.removeItem("has_session");
        localStorage.removeItem("cached_user");
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
      this.setSession(data.access_token);
      if (data.user && typeof window !== "undefined") {
        try {
          localStorage.setItem("cached_user", JSON.stringify(data.user));
        } catch {}
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
      // Pass through HTTP status to allow proper error handling in UI
      const err: any = new Error("Registration failed");
      err.status = res.status;
      throw err;
    }

    const payload = await res.json();
    const data = payload.data || payload;

    if (data.access_token) {
      this.setSession(data.access_token);
      if (data.user && typeof window !== "undefined") {
        try {
          localStorage.setItem("cached_user", JSON.stringify(data.user));
        } catch {}
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
    if (typeof window !== "undefined" && !localStorage.getItem("has_session")) {
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
        if (res.status === 401 || res.status === 403) {
          this.clearSession();
        }
        return null;
      }
      
      const payload = await res.json();
      const data = payload.data || payload;
      
      if (data.access_token) {
        this.setSession(data.access_token);
        if (data.user && typeof window !== "undefined") {
          try {
            localStorage.setItem("cached_user", JSON.stringify(data.user));
          } catch {}
        }
        return data;
      }
      return null;
    } catch {
      clearTimeout(timeoutId);
      // Transient error / timeout — do NOT clear valid session marker
      return null;
    }
  }
};
