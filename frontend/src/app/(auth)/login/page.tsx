"use client";

import { useState, useEffect, FormEvent, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Mail, Lock, Shield, ArrowRight } from "lucide-react";
import { useAppStore } from "@/store/useStore";
import { apiFetch, APIClientError } from "@/services/api";
import { sanitizeReturnUrl } from "@/lib/auth/safeReturnUrl";

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

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const getReturnUrl = useCallback(() => {
    if (typeof window === "undefined") return "/";
    const params = new URLSearchParams(window.location.search);
    const candidate =
      params.get("returnUrl") || params.get("redirect") || params.get("next");
    return sanitizeReturnUrl(candidate);
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (mounted && user) {
      router.push(getReturnUrl());
    }
  }, [mounted, user, router, getReturnUrl]);

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
        body: JSON.stringify({
          email: email.trim(),
          password,
          remember_me: rememberMe,
        }),
      });

      loginUser(data.user, data.access_token);
      router.push(getReturnUrl());
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

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white animate-spin rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-black text-white relative flex flex-col justify-between overflow-x-hidden select-none">
      {/* Background Graphic: Realistic Space Earth Globe & Starfield (Top-Left Aligned) */}
      <div className="fixed inset-0 pointer-events-none z-0 bg-black flex justify-start items-start overflow-hidden">
        <div className="relative w-full max-w-[970px] xl:max-w-[1115px] 2xl:max-w-[1240px] max-h-[75vh] aspect-[16/9]">
          <Image
            src="/images/login/globe-8k.jpg"
            alt="Orbital intelligence background"
            fill
            priority
            unoptimized={true}
            quality={100}
            sizes="(max-width: 1280px) 100vw, 1240px"
            className="object-contain"
          />
        </div>
      </div>

      {/* ================= MAIN CONTENT ================= */}
      <main className="w-full max-w-[1720px] mx-auto px-6 md:px-12 pt-6 sm:pt-8 md:pt-10 pb-4 flex-1 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-10 xl:gap-14 z-10">
        {/* LEFT COLUMN: HERO INTELLIGENCE (Top-Aligned) */}
        <section className="w-full lg:max-w-[58%] xl:max-w-[62%] flex flex-col justify-start self-start pt-0">
          {/* Eyebrow & Brand Headings */}
          <div className="flex flex-col mb-4">
            <p className="font-mono text-[10px] sm:text-[11px] tracking-[0.32em] text-neutral-400 uppercase font-medium mb-2.5">
              THE DAILY TECHNOLOGY INTELLIGENCE
            </p>

            <h1 className="text-4xl sm:text-5xl xl:text-6xl font-black tracking-tight text-white uppercase font-sans leading-[1.05]">
              TECH NEWS TODAY
            </h1>

            <p className="text-base sm:text-lg lg:text-xl text-neutral-300 font-light mt-2.5 leading-relaxed max-w-2xl">
              Your personal gateway to the technology that matters.
            </p>

            {/* Pillar Subtitle Strip */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] sm:text-[10px] font-mono tracking-[0.2em] text-neutral-500 uppercase mt-3.5">
              <span>BREAKING NEWS</span>
              <span className="text-neutral-700">/</span>
              <span>DEEP ANALYSIS</span>
              <span className="text-neutral-700">/</span>
              <span>EXPERT PERSPECTIVE</span>
              <span className="text-neutral-700">/</span>
              <span>A MORE INFORMED TOMORROW</span>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: LOGIN FORM CARD (Pure Black Glassmorphic) */}
        <section className="w-full lg:w-[440px] xl:w-[470px] shrink-0 self-center">
          <div className="bg-[#070709]/95 backdrop-blur-2xl border border-white/[0.12] rounded-[28px] p-7 sm:p-9 shadow-2xl shadow-black/95 relative">
            {/* Form Title & Subtitle */}
            <div className="mb-7">
              <h2 className="text-3xl sm:text-[34px] font-bold tracking-tight text-white font-sans leading-tight">
                Welcome back.
              </h2>
              <p className="text-xs sm:text-sm text-neutral-400 mt-2 font-normal">
                Sign in to continue to your intelligence desk.
              </p>
            </div>

            {/* Error Message Box */}
            {error && (
              <div
                className="mb-5 border border-red-500/30 bg-red-500/10 rounded-xl p-3 flex items-start gap-2.5 text-xs text-red-400 font-mono"
                aria-live="polite"
              >
                <span className="shrink-0 mt-0.5 font-bold">✕</span>
                <p className="leading-snug">{error}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4 sm:space-y-5">
              {/* Email Address */}
              <div>
                <label
                  htmlFor="email-field"
                  className="block font-mono text-[10px] tracking-[0.2em] uppercase text-neutral-400 font-semibold mb-2"
                >
                  EMAIL ADDRESS
                </label>
                <div className="relative flex items-center">
                  <Mail className="w-4 h-4 text-neutral-500 absolute left-4 pointer-events-none" />
                  <input
                    id="email-field"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    placeholder="operator@technews.today"
                    className="w-full bg-[#0e0e11] border border-neutral-800 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-neutral-500 outline-none focus:border-white/50 focus:ring-1 focus:ring-white/20 transition-all font-sans"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password-field"
                  className="block font-mono text-[10px] tracking-[0.2em] uppercase text-neutral-400 font-semibold mb-2"
                >
                  PASSWORD
                </label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 text-neutral-500 absolute left-4 pointer-events-none" />
                  <input
                    id="password-field"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                    placeholder="••••••••••••"
                    className="w-full bg-[#0e0e11] border border-neutral-800 rounded-xl pl-11 pr-16 py-3 text-sm text-white placeholder-neutral-500 outline-none focus:border-white/50 focus:ring-1 focus:ring-white/20 transition-all font-sans"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 text-[10px] font-mono font-bold tracking-wider text-neutral-400 hover:text-white uppercase px-1 py-1 transition-colors"
                  >
                    {showPassword ? "HIDE" : "SHOW"}
                  </button>
                </div>
              </div>

              {/* Remember Me & Forgot Password Row */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2.5 cursor-pointer text-neutral-400 select-none group">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-4 h-4 rounded border border-neutral-700 bg-[#0e0e11] flex items-center justify-center peer-checked:bg-white peer-checked:border-white transition-all">
                    {rememberMe && (
                      <svg
                        className="w-3 h-3 text-black stroke-[3.5]"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  <span className="group-hover:text-neutral-300 transition-colors">
                    Remember me
                  </span>
                </label>

                <Link
                  href="/forgot-password"
                  className="text-neutral-400 hover:text-white transition-colors underline-offset-4 hover:underline"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Primary Sign In Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-white hover:bg-neutral-100 active:scale-[0.99] text-black font-bold text-sm py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-white/5 transition-all mt-2 disabled:opacity-60 disabled:cursor-not-allowed font-sans"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    <span>Signing in...</span>
                  </div>
                ) : (
                  <>
                    <span>Sign in</span>
                    <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                  </>
                )}
              </button>
            </form>

            {/* Social Divider */}
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-[1px] bg-neutral-800" />
              <span className="font-mono text-[9px] tracking-[0.25em] text-neutral-500 uppercase font-semibold">
                OR CONTINUE WITH
              </span>
              <div className="flex-1 h-[1px] bg-neutral-800" />
            </div>

            {/* Social Authentication Buttons */}
            <div className="grid grid-cols-2 gap-3">
              {/* Continue with Google */}
              <button
                type="button"
                onClick={() => {
                  window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/auth/google`;
                }}
                className="w-full bg-[#0e0e11] hover:bg-[#151518] border border-neutral-800 hover:border-neutral-700 text-neutral-200 text-xs font-medium py-2.5 px-3 rounded-xl flex items-center justify-center gap-2.5 transition-all"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path
                    fill="#ffffff"
                    d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
                  />
                  <path
                    fill="#ffffff"
                    d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
                  />
                  <path
                    fill="#a1a1aa"
                    d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.8 0 12s.7 3.3 1.9 5.7l3.7-2.9z"
                  />
                  <path
                    fill="#71717a"
                    d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"
                  />
                </svg>
                <span className="truncate">Continue with Google</span>
              </button>

              {/* Continue with GitHub */}
              <button
                type="button"
                onClick={() => {
                  window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "/api/v1"}/auth/github`;
                }}
                className="w-full bg-[#0e0e11] hover:bg-[#151518] border border-neutral-800 hover:border-neutral-700 text-neutral-200 text-xs font-medium py-2.5 px-3 rounded-xl flex items-center justify-center gap-2.5 transition-all"
              >
                <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                  />
                </svg>
                <span className="truncate">Continue with GitHub</span>
              </button>
            </div>

            {/* Create Account Link */}
            <div className="mt-6 text-center text-xs text-neutral-400">
              <span>New to Tech News Today? </span>
              <Link
                href="/signup"
                className="text-white hover:underline font-semibold inline-flex items-center gap-1 transition-colors"
              >
                <span>Create an account</span>
                <ArrowRight className="w-3 h-3 stroke-[2.5]" />
              </Link>
            </div>
          </div>

          {/* Secure Session Guarantee */}
          <div className="flex items-center justify-center gap-2 mt-4 text-[11px] text-neutral-500 font-mono">
            <Shield className="w-3.5 h-3.5 text-neutral-500" />
            <span>Encrypted session</span>
            <span>•</span>
            <span>Secure authentication</span>
          </div>
        </section>
      </main>

      {/* ================= BOTTOM FOOTER BAR ================= */}
      <footer className="w-full px-6 md:px-12 py-4 flex items-center justify-between text-[10px] font-mono tracking-widest text-neutral-500 uppercase border-t border-white/[0.04] z-20">
        <div className="text-neutral-500">
          — IDEAS MOVE THE WORLD FORWARD.
        </div>

        <div className="flex items-center gap-2 text-neutral-400 font-medium">
          <span className="text-[11px]">❖</span>
          <span>TECH NEWS TODAY</span>
        </div>
      </footer>
    </div>
  );
}
