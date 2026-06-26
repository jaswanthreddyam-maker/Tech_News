"use client";

import { useState, useEffect, FormEvent, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GoogleLogin } from "@react-oauth/google";
import { useAppStore, User } from "@/store/useStore";
import { canAccessAdmin } from "@/lib/auth/permissions";
import { apiFetch, APIClientError } from "@/services/api";
import { Mail, Lock, ShieldCheck } from "lucide-react";
import { useTheme } from "next-themes";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    name: string;
    email: string;
    role: string;
    permissions: string[];
  };
}

export default function LoginPage() {
  const router = useRouter();
  const { user, loginUser } = useAppStore();
  const { resolvedTheme } = useTheme();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const redirectByRole = useCallback(
    (u: User | null) => {
      if (canAccessAdmin(u)) {
        router.push("/admin");
      } else {
        router.push("/");
      }
    },
    [router]
  );

  // If already authenticated, redirect
  useEffect(() => {
    if (mounted && user) {
      redirectByRole(user);
    }
  }, [mounted, user, redirectByRole]);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const data = await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password, remember_me: rememberMe }),
      });

      loginUser(data.user, data.access_token);
      redirectByRole(data.user);
    } catch (err: any) {
      if (err instanceof APIClientError) {
        if (err.status === 401) {
          setError("Invalid credentials. Check your email and password.");
        } else if (err.status === 403) {
          setError("Account suspended. Contact system administrator.");
        } else if (err.status === 429) {
          setError("Too many attempts. Try again in a few minutes.");
        } else {
          setError(err.message || "Authentication failed.");
        }
      } else {
        setError("Connection error. Verify the API gateway is online.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setError(null);
    setGoogleLoading(true);
    try {
      const data = await apiFetch<AuthResponse>("/auth/google", {
        method: "POST",
        body: JSON.stringify({ credential: credentialResponse.credential }),
      });
      loginUser(data.user, data.access_token);
      redirectByRole(data.user);
    } catch (err: any) {
      setError(err.message || "Google authentication failed.");
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError("Google Sign-In failed.");
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-neutral-300 dark:border-neutral-700 border-t-neutral-950 dark:border-t-white animate-spin rounded-full" />
      </div>
    );
  }

  const googleTheme = (resolvedTheme === "dark" ? "filled_black" : "outline") as "filled_black" | "outline";

  return (
    <div className="min-h-screen w-full bg-background flex flex-col items-center justify-center px-4 relative overflow-hidden animate-entrance select-none">
      {/* Background Engineering Grid and Circuit Traces */}
      <div className="absolute inset-0 border-grid opacity-[0.04] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,transparent_40%,var(--background)_100%)] pointer-events-none" />
      
      {/* CSS-only faint circuit traces */}
      <div className="absolute top-[15%] left-[5%] w-[150px] h-[1px] bg-neutral-300 dark:bg-neutral-800 opacity-20 hidden md:block">
        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-neutral-400 dark:bg-neutral-700" />
      </div>
      <div className="absolute top-[15%] left-[5%] w-[1px] h-[120px] bg-neutral-300 dark:bg-neutral-800 opacity-20 hidden md:block" />
      <div className="absolute top-[15%] left-[calc(5%+150px)] w-[100px] h-[1px] bg-neutral-300 dark:bg-neutral-800 opacity-20 origin-left rotate-[35deg] hidden md:block" />
      
      <div className="absolute bottom-[20%] right-[5%] w-[180px] h-[1px] bg-neutral-300 dark:bg-neutral-800 opacity-20 hidden md:block">
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-neutral-400 dark:bg-neutral-700" />
      </div>
      <div className="absolute bottom-[20%] right-[5%] w-[1px] h-[150px] bg-neutral-300 dark:bg-neutral-800 opacity-20 hidden md:block" />
      
      {/* Custom keyframes style for animated star and entrance */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes breathe {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
          }
        }
        .animate-breathe {
          animation: breathe 4s ease-in-out infinite;
        }
        @keyframes entrance {
          from {
            opacity: 0;
            transform: translateY(16px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-entrance {
          animation: entrance 600ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-entrance {
            animation: none;
            opacity: 1;
            transform: none;
          }
          .animate-breathe {
            animation: none;
          }
        }
      `}} />

      {/* Main viewport-constrained center content */}
      <div className="w-full max-w-[520px] flex flex-col gap-6 relative py-12">
        
        {/* Corner Brackets */}
        <div className="absolute top-2 left-2 w-8 h-8 border-t border-l border-neutral-300 dark:border-neutral-800 pointer-events-none" />
        <div className="absolute top-2 right-2 w-8 h-8 border-t border-r border-neutral-300 dark:border-neutral-800 pointer-events-none" />
        <div className="absolute bottom-2 left-2 w-8 h-8 border-b border-l border-neutral-300 dark:border-neutral-800 pointer-events-none" />
        <div className="absolute bottom-2 right-2 w-8 h-8 border-b border-r border-neutral-300 dark:border-neutral-800 pointer-events-none" />

        {/* Top Status Bar */}
        <div className="flex items-center justify-center gap-2 font-mono text-[9px] tracking-[0.25em] uppercase text-neutral-400 dark:text-neutral-500 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-neutral-950 dark:bg-white inline-block animate-pulse shrink-0" />
          <span>TECH NEWS TODAY • AUTONOMOUS NEWSROOM ACCESS</span>
        </div>

        {/* Logo and Titles */}
        <div className="text-center flex flex-col gap-4 mt-4">
          <div className="relative w-16 h-16 mx-auto rounded-full flex items-center justify-center border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-[#0d0d0d] shadow-sm animate-breathe">
            <div className="absolute inset-0 rounded-full bg-neutral-200/20 dark:bg-white/5 blur-md pointer-events-none" />
            <svg className="w-8 h-8 text-neutral-900 dark:text-white relative z-10" viewBox="0 0 100 100" fill="currentColor">
              <path d="M 50 15 Q 50 50 85 50 Q 50 50 50 85 Q 50 50 15 50 Q 50 50 50 15 Z" />
            </svg>
          </div>

          <div>
            <h1 className="text-3xl font-extrabold tracking-tighter text-neutral-950 dark:text-white font-sans uppercase">
              TECH NEWS TODAY
            </h1>
            <p className="font-mono text-[10px] tracking-[0.35em] uppercase text-neutral-500 dark:text-neutral-400 mt-2 font-bold">
              SECURE OPERATIONS PORTAL
            </p>
            <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
              Protected access for authorized operators only.
            </p>
          </div>
        </div>

        {/* Main Login Card */}
        <div className="w-full rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-[#0c0c0c] p-8 md:p-10 shadow-xl shadow-neutral-200/30 dark:shadow-none transition-all duration-300">
          
          {/* Error Banner */}
          {error && (
            <div className="mb-6 border border-red-500/20 bg-red-500/5 rounded-xl p-4 flex items-start gap-3" aria-live="polite">
              <svg className="w-4 h-4 text-red-500 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <p className="font-mono text-[11px] text-red-500 leading-relaxed font-semibold">{error}</p>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-6">
            {/* Email Address */}
            <div>
              <label htmlFor="login-email" className="block font-mono text-[10px] tracking-widest uppercase text-neutral-500 dark:text-neutral-400 mb-2 font-bold">
                EMAIL ADDRESS
              </label>
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500 group-focus-within:text-neutral-900 dark:group-focus-within:text-white transition-colors duration-150">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                  placeholder="operator@technews.today"
                  aria-invalid={error ? "true" : "false"}
                  className="w-full bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-800 rounded-xl pl-11 pr-4 py-3.5 text-sm text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-600 outline-none transition-all duration-100 focus:border-neutral-950 dark:focus:border-white focus:ring-2 focus:ring-neutral-950 dark:focus:ring-white/80 focus:ring-offset-2 dark:focus:ring-offset-[#0c0c0c] aria-[invalid=true]:border-red-500/50"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label htmlFor="login-password" className="block font-mono text-[10px] tracking-widest uppercase text-neutral-500 dark:text-neutral-400 mb-2 font-bold">
                PASSWORD
              </label>
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-500 group-focus-within:text-neutral-900 dark:group-focus-within:text-white transition-colors duration-150">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  placeholder="••••••••••••"
                  aria-invalid={error ? "true" : "false"}
                  className="w-full bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-800 rounded-xl pl-11 pr-16 py-3.5 text-sm text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-600 outline-none transition-all duration-100 focus:border-neutral-950 dark:focus:border-white focus:ring-2 focus:ring-neutral-950 dark:focus:ring-white/80 focus:ring-offset-2 dark:focus:ring-offset-[#0c0c0c] aria-[invalid=true]:border-red-500/50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 min-h-[44px] min-w-[44px] flex items-center justify-center font-mono text-[10px] tracking-widest uppercase text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-950 dark:focus-visible:ring-white rounded-md select-none"
                >
                  {showPassword ? "HIDE" : "SHOW"}
                </button>
              </div>
            </div>

            {/* Remember Session & Forgot Password */}
            <div className="flex items-center justify-between min-h-[44px]">
              <label className="flex items-center gap-3 cursor-pointer select-none group min-h-[44px]">
                <div className="relative flex items-center justify-center">
                  <input
                    id="login-remember"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-5.5 h-5.5 rounded-md border border-neutral-300 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50 flex items-center justify-center transition-all duration-100 peer-focus-visible:ring-2 peer-focus-visible:ring-neutral-950 dark:peer-focus-visible:ring-white peer-checked:bg-neutral-950 dark:peer-checked:bg-white peer-checked:border-neutral-950 dark:peer-checked:border-white">
                    {rememberMe && (
                      <svg className="w-3.5 h-3.5 text-white dark:text-black" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                </div>
                <span className="font-mono text-[11px] tracking-wider uppercase text-neutral-500 dark:text-neutral-400 group-hover:text-neutral-900 dark:group-hover:text-white transition-colors duration-150">
                  Remember Session
                </span>
              </label>
              <button
                type="button"
                className="font-mono text-[11px] tracking-wider text-neutral-500 dark:text-neutral-400 hover:text-neutral-950 dark:hover:text-white transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-950 dark:focus-visible:ring-white rounded px-1"
              >
                Forgot Password?
              </button>
            </div>

            {/* Submit Button */}
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 font-mono text-xs uppercase tracking-[0.2em] font-bold py-4 rounded-xl transition-all duration-300 cubic-bezier(0.34, 1.56, 0.64, 1) hover:-translate-y-0.5 hover:scale-[1.02] active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-neutral-950 dark:focus-visible:ring-white bg-neutral-950 dark:bg-white text-white dark:text-black hover:bg-neutral-900 dark:hover:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:scale-100 shadow-md"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  <span>AUTHENTICATING</span>
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4" />
                  <span>SECURE LOGIN</span>
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-neutral-200 dark:bg-neutral-800" />
            <span className="font-mono text-[10px] text-neutral-400 dark:text-neutral-500 tracking-[0.2em] font-bold">OR</span>
            <div className="flex-1 h-px bg-neutral-200 dark:bg-neutral-800" />
          </div>

          {/* Google Sign In */}
          <div className="w-full flex justify-center min-h-[44px]">
            {googleLoading ? (
              <div className="w-full border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/50 rounded-xl py-3.5 flex items-center justify-center">
                <svg className="animate-spin h-4 w-4 text-neutral-500" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
              </div>
            ) : (
              <div className="w-full relative [&>div]:!w-full [&>div>div]:!w-full [&_iframe]:!w-full">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  theme={googleTheme}
                  shape="rectangular"
                  text="signin_with"
                  size="large"
                />
              </div>
            )}
          </div>

          {/* Create Account redirect */}
          <div className="mt-6 text-center font-mono text-[10px] tracking-wider text-neutral-500 dark:text-neutral-400 border-t border-neutral-200 dark:border-neutral-800 pt-6 select-none">
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="text-neutral-950 dark:text-white hover:underline uppercase font-bold transition-colors duration-150 focus:outline-none focus-visible:ring-1 focus-visible:ring-neutral-950 dark:focus-visible:ring-white rounded px-1"
            >
              Create Account
            </Link>
          </div>
        </div>

        {/* Bottom System Status */}
        <div className="w-full rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-[#0c0c0c] p-4 flex items-center justify-between shadow-md dark:shadow-none transition-all duration-300">
          <div className="flex items-start gap-3">
            <span className="h-2 w-2 rounded-full bg-neutral-950 dark:bg-white inline-block animate-pulse mt-1.5 shrink-0" />
            <div>
              <h3 className="font-mono text-[10px] tracking-wider font-bold text-neutral-950 dark:text-white uppercase">
                SYSTEM STATUS: OPERATIONAL
              </h3>
              <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5 font-medium">
                All systems secure and monitored
              </p>
            </div>
          </div>
          <ShieldCheck className="w-5 h-5 text-neutral-950 dark:text-white shrink-0" />
        </div>
      </div>
    </div>
  );
}
