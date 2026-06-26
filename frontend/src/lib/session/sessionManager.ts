const API_BASE_URL = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
  : (process.env.INTERNAL_API_URL || "http://localhost:8000/api/v1");

// In-memory access token storage (never stored in localStorage)
let accessToken: string | null = null;
let tokenExpiresAt: number | null = null;

// The backend handles the HttpOnly refresh token cookie automatically

export const sessionManager = {
  isAuthenticated(): boolean {
    if (!accessToken || !tokenExpiresAt) return false;
    return Date.now() < tokenExpiresAt - 10000;
  },

  getAccessToken(): string | null {
    return this.isAuthenticated() ? accessToken : null;
  },

  setSession(token: string, expiresInSeconds: number = 900) {
    accessToken = token;
    tokenExpiresAt = Date.now() + (expiresInSeconds * 1000);
  },

  clearSession() {
    accessToken = null;
    tokenExpiresAt = null;
  },

  async login(credentials: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials)
    });
    
    if (!res.ok) throw new Error("Login failed");
    
    const payload = await res.json();
    const data = payload.data || payload;
    
    if (data.access_token) {
      this.setSession(data.access_token);
    }
    return data;
  },

  async register(details: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
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
    }
    return data;
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST" });
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (e) {
      // eslint-disable-next-line no-console

    } finally {
      this.clearSession();
    }
  },

  async refresh(): Promise<any> {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include"
      });
      if (!res.ok) throw new Error("Refresh failed");
      
      const payload = await res.json();
      const data = payload.data || payload;
      
      if (data.access_token) {
        this.setSession(data.access_token);
        return data;
      }
      return null;
    } catch (e) {
      this.clearSession();
      throw e;
    }
  }
};
