"use client";

import { useState, useEffect, FormEvent, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  Mail,
  Lock,
  Shield,
  ArrowRight,
  AlertCircle,
  User as UserIcon,
  Check,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore, User } from "@/store/useStore";
import { apiFetch, APIClientError } from "@/services/api";
import { sanitizeReturnUrl } from "@/lib/auth/safeReturnUrl";
import { sessionManager } from "@/lib/session/sessionManager";
import { PERMISSIONS } from "@/lib/auth/permissions";
import { GoogleLogin } from "@react-oauth/google";

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    name: string;
    email: string;
    role: string;
    status: string;
    permissions?: string[];
  };
}

type AuthStatus = "IDLE" | "SUBMITTING" | "SUCCESS" | "ERROR" | "RATE_LIMITED" | "NETWORK_ERROR";

interface OAuthState {
  provider: "google" | "github";
  status: "connecting" | "error";
  message?: string;
}

export default function LoginPage() {
  const router = useRouter();
  const { user, loginUser } = useAppStore();

  // Auth Mode: "signin" | "signup"
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");

  // Shared Fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus>("IDLE");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [oauthState, setOauthState] = useState<OAuthState | null>(null);
  const [mounted, setMounted] = useState(false);

  // Sign In Specific State
  const [rememberMe, setRememberMe] = useState(false);

  // Sign Up Specific States
  const [name, setName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(true);

  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const modeParam = params.get("mode") || params.get("tab");
      if (modeParam === "signup" || modeParam === "register") {
        setAuthMode("signup");
      }
    }
  }, []);

  const switchMode = (newMode: "signin" | "signup") => {
    setAuthMode(newMode);
    setErrorMessage(null);
    setOauthState(null);
    setAuthStatus("IDLE");

    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (newMode === "signup") {
        url.searchParams.set("mode", "signup");
      } else {
        url.searchParams.delete("mode");
      }
      window.history.replaceState({}, "", url.pathname + (url.search ? url.search : ""));
    }
  };

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

  // Live password validation criteria checks for signup
  const passHasMinLength = password.length >= 8;
  const passHasUppercase = /[A-Z]/.test(password);
  const passHasLowercase = /[a-z]/.test(password);
  const passHasNumber = /[0-9]/.test(password);
  const passMatchesConfirm =
    confirmPassword.length > 0 && password === confirmPassword;
  const isSignupPasswordValid =
    passHasMinLength && passHasUppercase && passHasLowercase && passHasNumber;

  const handleAuthSuccess = useCallback(
    (data: AuthResponse) => {
      // Extract permissions from JWT payload claims if available
      let permissions: string[] = [];
      try {
        const parts = data.access_token.split(".");
        if (parts.length >= 2) {
          const payloadJson = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
          const decoded = JSON.parse(payloadJson);
          if (Array.isArray(decoded.permissions)) {
            permissions = decoded.permissions;
          }
        }
      } catch {
        // Fallback if parsing fails
      }

      if (
        permissions.length === 0 &&
        (data.user.role === "super_admin" || data.user.role === "admin")
      ) {
        permissions = Object.values(PERMISSIONS);
      }

      const fullUser: User = {
        id: data.user.id,
        name: data.user.name,
        email: data.user.email,
        role: data.user.role,
        permissions: data.user.permissions || permissions,
      };

      // Extended session persistence: 28 days if Remember me is checked, standard 7 days otherwise
      const sessionTtl = rememberMe ? 28 * 86400 : 7 * 86400;
      sessionManager.setSession(data.access_token, sessionTtl);
      sessionManager.setCachedUser(fullUser);
      loginUser(fullUser, data.access_token);
      setAuthStatus("SUCCESS");

      const targetUrl = getReturnUrl();
      if (
        targetUrl === "/" &&
        (fullUser.role === "super_admin" || fullUser.role === "admin")
      ) {
        router.push("/dashboard");
      } else {
        router.push(targetUrl);
      }
    },
    [rememberMe, loginUser, getReturnUrl, router]
  );

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (authStatus === "SUBMITTING") return;

    setErrorMessage(null);
    setOauthState(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setAuthStatus("ERROR");
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setAuthStatus("ERROR");
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setAuthStatus("ERROR");
      setErrorMessage("Password is required.");
      return;
    }

    setAuthStatus("SUBMITTING");

    try {
      const data = await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: trimmedEmail,
          password,
          remember_me: rememberMe,
        }),
      });

      handleAuthSuccess(data);
    } catch (err: any) {
      if (err instanceof APIClientError) {
        if (err.status === 401 || err.status === 403) {
          setAuthStatus("ERROR");
          setErrorMessage("Invalid email or password.");
        } else if (err.status === 429) {
          setAuthStatus("RATE_LIMITED");
          setErrorMessage("Too many sign-in attempts. Please wait a moment and try again.");
        } else {
          setAuthStatus("ERROR");
          setErrorMessage("Unable to sign you in right now. Please try again in a moment.");
        }
      } else {
        setAuthStatus("NETWORK_ERROR");
        setErrorMessage("Unable to sign you in right now. Please check your connection.");
      }
    }
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    if (authStatus === "SUBMITTING") return;

    setErrorMessage(null);
    setOauthState(null);

    const trimmedName = name.trim();
    if (!trimmedName || trimmedName.length < 2) {
      setAuthStatus("ERROR");
      setErrorMessage("Please enter your full name (minimum 2 characters).");
      return;
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setAuthStatus("ERROR");
      setErrorMessage("Please enter an email address.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setAuthStatus("ERROR");
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!isSignupPasswordValid) {
      setAuthStatus("ERROR");
      setErrorMessage(
        "Password must be at least 8 characters long and contain uppercase, lowercase, and a number."
      );
      return;
    }

    if (password !== confirmPassword) {
      setAuthStatus("ERROR");
      setErrorMessage("Passwords do not match. Please verify both password fields.");
      return;
    }

    if (!agreeTerms) {
      setAuthStatus("ERROR");
      setErrorMessage("Please accept the Terms of Service to continue.");
      return;
    }

    setAuthStatus("SUBMITTING");

    try {
      const data = await apiFetch<AuthResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          name: trimmedName,
          email: trimmedEmail.toLowerCase(),
          password,
        }),
      });

      handleAuthSuccess(data);
    } catch (err: any) {
      if (err instanceof APIClientError) {
        if (
          err.status === 409 ||
          err.message?.toLowerCase().includes("already registered") ||
          err.message?.toLowerCase().includes("exists")
        ) {
          setAuthStatus("ERROR");
          setErrorMessage("An account with this email already exists. You can sign in below.");
        } else if (err.status === 429) {
          setAuthStatus("RATE_LIMITED");
          setErrorMessage("Too many registration attempts. Please wait a moment and try again.");
        } else {
          setAuthStatus("ERROR");
          setErrorMessage(err.message || "Unable to create your account. Please try again.");
        }
      } else {
        setAuthStatus("NETWORK_ERROR");
        setErrorMessage("Unable to connect to the authentication server. Please check your connection.");
      }
    }
  };

  const handleGoogleSuccess = async (credential: string) => {
    setErrorMessage(null);
    setOauthState({ provider: "google", status: "connecting" });
    try {
      const data = await apiFetch<AuthResponse>("/auth/google", {
        method: "POST",
        body: JSON.stringify({ credential }),
      });
      handleAuthSuccess(data);
    } catch (err: any) {
      setOauthState({
        provider: "google",
        status: "error",
        message: err?.message || "Unable to complete Google authentication. Please try again.",
      });
    }
  };

  const handleGoogleError = (msg: string) => {
    setOauthState({
      provider: "google",
      status: "error",
      message: msg,
    });
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
      {/* Background Graphic: Realistic Space Earth Globe & Starfield (Bottom-Left Corner Aligned) */}
      <div className="fixed inset-0 pointer-events-none z-0 bg-black flex justify-start items-end overflow-hidden">
        <div className="relative w-full max-w-[970px] xl:max-w-[1115px] 2xl:max-w-[1240px] max-h-[75vh] aspect-[1000/564]">
          <Image
            src="/images/login/globe-space.jpg"
            alt="Orbital intelligence background"
            fill
            priority
            unoptimized={true}
            quality={100}
            sizes="(max-width: 1280px) 100vw, 1240px"
            className="object-contain object-left-bottom"
          />
        </div>
      </div>

      {/* ================= MAIN CONTENT ================= */}
      <main className="w-full max-w-[1720px] mx-auto px-4 sm:px-6 md:px-12 pt-6 sm:pt-8 md:pt-10 pb-6 flex-1 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-10 xl:gap-14 z-10">
        {/* LEFT COLUMN: HERO INTELLIGENCE (Top-Aligned) */}
        <section className="w-full lg:max-w-[58%] xl:max-w-[62%] flex flex-col justify-start self-start pt-0">
          <div className="flex flex-col mb-4">
            <p className="font-mono text-[10px] sm:text-[11px] tracking-[0.32em] text-neutral-300 uppercase font-medium mb-2.5">
              THE DAILY TECHNOLOGY INTELLIGENCE
            </p>

            <h1 className="text-4xl sm:text-5xl xl:text-6xl font-black tracking-tight text-white uppercase font-sans leading-[1.05]">
              TECH NEWS TODAY
            </h1>

            <p className="text-base sm:text-lg lg:text-xl text-neutral-300 font-light mt-2.5 leading-relaxed max-w-2xl">
              Your personal gateway to the technology that matters.
            </p>

            {/* Pillar Subtitle Strip */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] sm:text-[10px] font-mono tracking-[0.2em] text-neutral-400 uppercase mt-3.5">
              <span>BREAKING NEWS</span>
              <span className="text-neutral-600">/</span>
              <span>DEEP ANALYSIS</span>
              <span className="text-neutral-600">/</span>
              <span>EXPERT PERSPECTIVE</span>
              <span className="text-neutral-600">/</span>
              <span>A MORE INFORMED TOMORROW</span>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: DYNAMIC AUTH CARD (SIGN IN / SIGN UP) */}
        <section className="w-full max-w-[440px] xl:max-w-[460px] mx-auto lg:mx-0 shrink-0 self-center">
          <div className="bg-[#08090B] border border-white/[0.14] rounded-[24px] p-5 sm:p-7 md:p-8 shadow-2xl shadow-black/80 relative max-h-[calc(100vh-48px)] overflow-y-auto">
            
            {/* Error Message Announcement Box */}
            {errorMessage && (
              <div
                id="auth-error-msg"
                role="alert"
                aria-live="polite"
                className="mb-4 border border-red-500/30 bg-red-500/10 rounded-[12px] p-3 flex items-start justify-between gap-2 text-xs text-red-300"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" aria-hidden="true" />
                  <p className="leading-snug">{errorMessage}</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setAuthStatus("IDLE");
                  }}
                  aria-label="Dismiss error notice"
                  className="text-red-400 hover:text-red-200 shrink-0 text-xs px-1 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-red-400 rounded"
                >
                  ✕
                </button>
              </div>
            )}

            {/* OAuth Notice Announcement Box */}
            {oauthState?.status === "error" && oauthState.message && (
              <div
                role="alert"
                aria-live="polite"
                className="mb-4 border border-amber-500/30 bg-amber-500/10 rounded-[12px] p-3 flex items-start justify-between gap-2 text-xs text-amber-300"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
                  <p className="leading-snug">{oauthState.message}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setOauthState(null)}
                  aria-label="Dismiss notice"
                  className="text-amber-400 hover:text-amber-200 shrink-0 text-xs px-1 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-400 rounded"
                >
                  ✕
                </button>
              </div>
            )}

            <AnimatePresence mode="wait" initial={false}>
              {authMode === "signin" ? (
                /* ================= SIGN IN VIEW ================= */
                <motion.div
                  key="signin-view"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  {/* Header */}
                  <div className="mb-6 sm:mb-7">
                    <h2 className="text-3xl sm:text-[34px] font-bold tracking-tight text-white font-sans leading-tight">
                      Welcome back.
                    </h2>
                    <p className="text-xs sm:text-sm text-neutral-200 mt-2 font-normal">
                      Sign in to your Intelligence Desk.
                    </p>
                  </div>

                  <form onSubmit={handleLogin} className="space-y-4 sm:space-y-5" noValidate>
                    {/* Email Field */}
                    <div className="space-y-2">
                      <label
                        htmlFor="login-email"
                        className="block font-mono text-[11px] tracking-[0.2em] uppercase text-neutral-200 font-semibold"
                      >
                        Email Address
                      </label>
                      <div className="relative flex items-center">
                        <Mail className="w-5 h-5 text-neutral-400 absolute left-4 pointer-events-none" aria-hidden="true" />
                        <input
                          id="login-email"
                          name="email"
                          type="email"
                          autoComplete="email"
                          value={email}
                          onChange={(e) => {
                            setEmail(e.target.value);
                            if (authStatus === "ERROR") {
                              setAuthStatus("IDLE");
                              setErrorMessage(null);
                            }
                          }}
                          required
                          aria-required="true"
                          aria-describedby={errorMessage ? "auth-error-msg" : undefined}
                          placeholder="operator@technews.today"
                          className="w-full h-[54px] sm:h-[56px] bg-[#0E1013] border border-neutral-700/80 rounded-[12px] pl-12 pr-4 text-sm text-white placeholder-neutral-400 focus:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#08090B] transition-all font-sans"
                        />
                      </div>
                    </div>

                    {/* Password Field */}
                    <div className="space-y-2">
                      <label
                        htmlFor="login-password"
                        className="block font-mono text-[11px] tracking-[0.2em] uppercase text-neutral-200 font-semibold"
                      >
                        Password
                      </label>
                      <div className="relative flex items-center">
                        <Lock className="w-5 h-5 text-neutral-400 absolute left-4 pointer-events-none" aria-hidden="true" />
                        <input
                          id="login-password"
                          name="password"
                          type={showPassword ? "text" : "password"}
                          autoComplete="current-password"
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (authStatus === "ERROR") {
                              setAuthStatus("IDLE");
                              setErrorMessage(null);
                            }
                          }}
                          required
                          aria-required="true"
                          aria-describedby={errorMessage ? "auth-error-msg" : undefined}
                          placeholder="••••••••••••"
                          className="w-full h-[54px] sm:h-[56px] bg-[#0E1013] border border-neutral-700/80 rounded-[12px] pl-12 pr-20 text-sm text-white placeholder-neutral-400 focus:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#08090B] transition-all font-sans"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          aria-label={showPassword ? "Hide password" : "Show password"}
                          aria-pressed={showPassword}
                          className="absolute right-3 h-9 px-2.5 rounded-lg text-xs font-mono font-medium text-neutral-300 hover:text-white hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-1 focus-visible:ring-offset-[#0E1013] transition-colors cursor-pointer select-none"
                        >
                          {showPassword ? "Hide" : "Show"}
                        </button>
                      </div>
                    </div>

                    {/* Remember Me & Forgot Password Row */}
                    <div className="flex items-center justify-between text-xs pt-1">
                      <label
                        htmlFor="remember-me"
                        className="flex items-center gap-2.5 cursor-pointer text-neutral-200 select-none group"
                      >
                        <input
                          id="remember-me"
                          name="remember_me"
                          type="checkbox"
                          checked={rememberMe}
                          onChange={(e) => setRememberMe(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-4 h-4 rounded border border-neutral-600 bg-[#0E1013] flex items-center justify-center peer-checked:bg-white peer-checked:border-white peer-focus-visible:ring-2 peer-focus-visible:ring-white peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-[#08090B] transition-all">
                          {rememberMe && (
                            <svg
                              className="w-3 h-3 text-black stroke-[3.5]"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              aria-hidden="true"
                            >
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          )}
                        </div>
                        <span className="group-hover:text-white transition-colors">
                          Remember me
                        </span>
                      </label>

                      <Link
                        href="/forgot-password"
                        className="text-neutral-200 hover:text-white font-semibold cursor-pointer underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#08090B] rounded transition-colors"
                      >
                        Forgot password?
                      </Link>
                    </div>

                    {/* Submit Button */}
                    <button
                      type="submit"
                      disabled={authStatus === "SUBMITTING"}
                      className="group w-full h-[56px] sm:h-[60px] bg-white hover:bg-neutral-100 active:scale-[0.99] text-black font-semibold text-sm rounded-[12px] flex items-center justify-center gap-2 shadow-lg shadow-white/5 transition-all mt-2 disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#08090B]"
                    >
                      {authStatus === "SUBMITTING" ? (
                        <div className="flex items-center gap-2.5">
                          <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" aria-hidden="true" />
                          <span>Signing in...</span>
                        </div>
                      ) : (
                        <>
                          <span>Sign in</span>
                          <ArrowRight className="w-4 h-4 stroke-[2.5] group-hover:translate-x-1 transition-transform duration-200" aria-hidden="true" />
                        </>
                      )}
                    </button>
                  </form>

                  {/* Social Divider */}
                  <div className="flex items-center gap-3 my-5 sm:my-6">
                    <div className="flex-1 h-[1px] bg-neutral-800" />
                    <span className="font-mono text-[10px] tracking-[0.25em] text-neutral-400 uppercase font-semibold">
                      OR
                    </span>
                    <div className="flex-1 h-[1px] bg-neutral-800" />
                  </div>

                  {/* Google OAuth Button */}
                  <div className="flex flex-col items-center justify-center gap-3">
                    {Boolean(
                      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID &&
                      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID !== "disabled" &&
                      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID !== "undefined"
                    ) ? (
                      <div className="w-full flex justify-center py-0.5">
                        <GoogleLogin
                          onSuccess={(credentialResponse) => {
                            if (credentialResponse.credential) {
                              handleGoogleSuccess(credentialResponse.credential);
                            } else {
                              handleGoogleError("Google Sign-In failed to return credentials.");
                            }
                          }}
                          onError={() => handleGoogleError("Google Sign-In was cancelled or failed.")}
                          theme="filled_black"
                          shape="pill"
                          size="large"
                          text="continue_with"
                          width="380"
                        />
                      </div>
                    ) : (
                      <div className="w-full text-center text-xs text-neutral-400">
                        Google sign-in is not configured.
                      </div>
                    )}
                  </div>

                  {/* Toggle to Sign Up */}
                  <div className="mt-5 sm:mt-6 text-center text-xs text-neutral-200">
                    <span>New to Tech News Today? </span>
                    <button
                      type="button"
                      id="toggle-to-signup"
                      onClick={() => switchMode("signup")}
                      className="text-white hover:underline font-semibold inline-flex items-center gap-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#08090B] rounded cursor-pointer"
                    >
                      <span>Create an account</span>
                      <ArrowRight className="w-3 h-3 stroke-[2.5]" aria-hidden="true" />
                    </button>
                  </div>
                </motion.div>
              ) : (
                /* ================= SIGN UP VIEW ================= */
                <motion.div
                  key="signup-view"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  {/* Header */}
                  <div className="mb-4 sm:mb-5">
                    <h2 className="text-2xl sm:text-[30px] font-bold tracking-tight text-white font-sans leading-tight">
                      Create an account.
                    </h2>
                    <p className="text-xs text-neutral-300 mt-1 font-normal">
                      Sign up for your Intelligence Desk.
                    </p>
                  </div>

                  <form onSubmit={handleRegister} className="space-y-3 sm:space-y-3.5" noValidate>
                    {/* Full Name Field */}
                    <div className="space-y-1">
                      <label
                        htmlFor="signup-name"
                        className="block font-mono text-[10px] tracking-[0.2em] uppercase text-neutral-300 font-semibold"
                      >
                        Full Name
                      </label>
                      <div className="relative flex items-center">
                        <UserIcon className="w-4 h-4 text-neutral-400 absolute left-3.5 pointer-events-none" aria-hidden="true" />
                        <input
                          id="signup-name"
                          name="name"
                          type="text"
                          autoComplete="name"
                          value={name}
                          onChange={(e) => {
                            setName(e.target.value);
                            if (authStatus === "ERROR") {
                              setAuthStatus("IDLE");
                              setErrorMessage(null);
                            }
                          }}
                          required
                          aria-required="true"
                          placeholder="Operator Name"
                          className="w-full h-[46px] sm:h-[48px] bg-[#0E1013] border border-neutral-700/80 rounded-[10px] pl-10 pr-4 text-xs sm:text-sm text-white placeholder-neutral-400 focus:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white transition-all font-sans"
                        />
                      </div>
                    </div>

                    {/* Email Field */}
                    <div className="space-y-1">
                      <label
                        htmlFor="signup-email"
                        className="block font-mono text-[10px] tracking-[0.2em] uppercase text-neutral-300 font-semibold"
                      >
                        Email Address
                      </label>
                      <div className="relative flex items-center">
                        <Mail className="w-4 h-4 text-neutral-400 absolute left-3.5 pointer-events-none" aria-hidden="true" />
                        <input
                          id="signup-email"
                          name="email"
                          type="email"
                          autoComplete="email"
                          value={email}
                          onChange={(e) => {
                            setEmail(e.target.value);
                            if (authStatus === "ERROR") {
                              setAuthStatus("IDLE");
                              setErrorMessage(null);
                            }
                          }}
                          required
                          aria-required="true"
                          placeholder="operator@technews.today"
                          className="w-full h-[46px] sm:h-[48px] bg-[#0E1013] border border-neutral-700/80 rounded-[10px] pl-10 pr-4 text-xs sm:text-sm text-white placeholder-neutral-400 focus:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white transition-all font-sans"
                        />
                      </div>
                    </div>

                    {/* Password Field */}
                    <div className="space-y-1">
                      <label
                        htmlFor="signup-password"
                        className="block font-mono text-[10px] tracking-[0.2em] uppercase text-neutral-300 font-semibold"
                      >
                        Password
                      </label>
                      <div className="relative flex items-center">
                        <Lock className="w-4 h-4 text-neutral-400 absolute left-3.5 pointer-events-none" aria-hidden="true" />
                        <input
                          id="signup-password"
                          name="password"
                          type={showPassword ? "text" : "password"}
                          autoComplete="new-password"
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (authStatus === "ERROR") {
                              setAuthStatus("IDLE");
                              setErrorMessage(null);
                            }
                          }}
                          required
                          aria-required="true"
                          placeholder="••••••••••••"
                          className="w-full h-[46px] sm:h-[48px] bg-[#0E1013] border border-neutral-700/80 rounded-[10px] pl-10 pr-16 text-xs sm:text-sm text-white placeholder-neutral-400 focus:border-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white transition-all font-sans"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          aria-label={showPassword ? "Hide password" : "Show password"}
                          className="absolute right-2.5 h-7 px-2 rounded text-[11px] font-mono font-medium text-neutral-300 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer select-none"
                        >
                          {showPassword ? "Hide" : "Show"}
                        </button>
                      </div>

                      {/* Real-time Password Requirements */}
                      <div className="pt-0.5 flex flex-wrap gap-1">
                        <span className={`inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded-full border transition-colors ${passHasMinLength ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 bg-[#0E1013] text-neutral-500"}`}>
                          <span className={`w-1 h-1 rounded-full ${passHasMinLength ? "bg-emerald-400" : "bg-neutral-600"}`} />
                          8+ chars
                        </span>
                        <span className={`inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded-full border transition-colors ${passHasUppercase ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 bg-[#0E1013] text-neutral-500"}`}>
                          <span className={`w-1 h-1 rounded-full ${passHasUppercase ? "bg-emerald-400" : "bg-neutral-600"}`} />
                          Uppercase
                        </span>
                        <span className={`inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded-full border transition-colors ${passHasLowercase ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 bg-[#0E1013] text-neutral-500"}`}>
                          <span className={`w-1 h-1 rounded-full ${passHasLowercase ? "bg-emerald-400" : "bg-neutral-600"}`} />
                          Lowercase
                        </span>
                        <span className={`inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded-full border transition-colors ${passHasNumber ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-neutral-800 bg-[#0E1013] text-neutral-500"}`}>
                          <span className={`w-1 h-1 rounded-full ${passHasNumber ? "bg-emerald-400" : "bg-neutral-600"}`} />
                          Number
                        </span>
                      </div>
                    </div>

                    {/* Confirm Password Field */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <label
                          htmlFor="signup-confirm-password"
                          className="block font-mono text-[10px] tracking-[0.2em] uppercase text-neutral-300 font-semibold"
                        >
                          Confirm Password
                        </label>
                        {confirmPassword.length > 0 && (
                          <span className={`text-[9px] font-mono font-semibold tracking-wider ${passMatchesConfirm ? "text-emerald-400" : "text-red-400"}`}>
                            {passMatchesConfirm ? "✓ MATCH" : "✗ MISMATCH"}
                          </span>
                        )}
                      </div>
                      <div className="relative flex items-center">
                        <Lock className="w-4 h-4 text-neutral-400 absolute left-3.5 pointer-events-none" aria-hidden="true" />
                        <input
                          id="signup-confirm-password"
                          name="confirm_password"
                          type={showConfirmPassword ? "text" : "password"}
                          autoComplete="new-password"
                          value={confirmPassword}
                          onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            if (authStatus === "ERROR") {
                              setAuthStatus("IDLE");
                              setErrorMessage(null);
                            }
                          }}
                          required
                          aria-required="true"
                          placeholder="••••••••••••"
                          className={`w-full h-[46px] sm:h-[48px] bg-[#0E1013] border rounded-[10px] pl-10 pr-16 text-xs sm:text-sm text-white placeholder-neutral-400 focus:outline-none transition-all font-sans ${
                            confirmPassword.length > 0
                              ? passMatchesConfirm
                                ? "border-emerald-500/60 focus:border-emerald-400 focus-visible:ring-2 focus-visible:ring-emerald-400/50"
                                : "border-red-500/60 focus:border-red-400 focus-visible:ring-2 focus-visible:ring-red-400/50"
                              : "border-neutral-700/80 focus:border-white focus-visible:ring-2 focus-visible:ring-white"
                          }`}
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                          className="absolute right-2.5 h-7 px-2 rounded text-[11px] font-mono font-medium text-neutral-300 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer select-none"
                        >
                          {showConfirmPassword ? "Hide" : "Show"}
                        </button>
                      </div>
                    </div>

                    {/* Terms Checkbox */}
                    <div className="flex items-start gap-2 text-xs pt-0.5">
                      <label
                        htmlFor="signup-agree-terms"
                        className="flex items-start gap-2 cursor-pointer text-neutral-300 select-none group"
                      >
                        <input
                          id="signup-agree-terms"
                          name="agree_terms"
                          type="checkbox"
                          checked={agreeTerms}
                          onChange={(e) => setAgreeTerms(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-3.5 h-3.5 mt-0.5 rounded border border-neutral-600 bg-[#0E1013] flex items-center justify-center peer-checked:bg-white peer-checked:border-white peer-focus-visible:ring-2 peer-focus-visible:ring-white transition-all shrink-0">
                          {agreeTerms && (
                            <Check className="w-3 h-3 text-black stroke-[3.5]" aria-hidden="true" />
                          )}
                        </div>
                        <span className="text-[10px] text-neutral-300 leading-snug group-hover:text-white transition-colors">
                          I agree to the Terms of Service & Privacy Policy
                        </span>
                      </label>
                    </div>

                    {/* Submit Button */}
                    <button
                      type="submit"
                      disabled={authStatus === "SUBMITTING"}
                      className="group w-full h-[48px] sm:h-[50px] bg-white hover:bg-neutral-100 active:scale-[0.99] text-black font-semibold text-xs sm:text-sm rounded-[10px] flex items-center justify-center gap-2 shadow-lg shadow-white/5 transition-all mt-1 disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
                    >
                      {authStatus === "SUBMITTING" ? (
                        <div className="flex items-center gap-2">
                          <span className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" aria-hidden="true" />
                          <span>Creating account...</span>
                        </div>
                      ) : (
                        <>
                          <span>Create account</span>
                          <ArrowRight className="w-3.5 h-3.5 stroke-[2.5] group-hover:translate-x-1 transition-transform duration-200" aria-hidden="true" />
                        </>
                      )}
                    </button>
                  </form>

                  {/* Social Divider */}
                  <div className="flex items-center gap-3 my-3.5 sm:my-4">
                    <div className="flex-1 h-[1px] bg-neutral-800" />
                    <span className="font-mono text-[9px] tracking-[0.25em] text-neutral-400 uppercase font-semibold">
                      OR
                    </span>
                    <div className="flex-1 h-[1px] bg-neutral-800" />
                  </div>

                  {/* Google OAuth Button */}
                  <div className="flex flex-col items-center justify-center gap-2">
                    {Boolean(
                      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID &&
                      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID !== "disabled" &&
                      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID !== "undefined"
                    ) ? (
                      <div className="w-full flex justify-center py-0.5 scale-[0.95] origin-center">
                        <GoogleLogin
                          onSuccess={(credentialResponse) => {
                            if (credentialResponse.credential) {
                              handleGoogleSuccess(credentialResponse.credential);
                            } else {
                              handleGoogleError("Google Sign-In failed to return credentials.");
                            }
                          }}
                          onError={() => handleGoogleError("Google Sign-In was cancelled or failed.")}
                          theme="filled_black"
                          shape="pill"
                          size="large"
                          text="continue_with"
                          width="360"
                        />
                      </div>
                    ) : (
                      <div className="w-full text-center text-xs text-neutral-400">
                        Google sign-in is not configured.
                      </div>
                    )}
                  </div>

                  {/* Toggle back to Sign In */}
                  <div className="mt-3.5 sm:mt-4 text-center text-xs text-neutral-200">
                    <span>Already have an account? </span>
                    <button
                      type="button"
                      id="toggle-to-signin"
                      onClick={() => switchMode("signin")}
                      className="text-white hover:underline font-semibold inline-flex items-center gap-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white rounded cursor-pointer"
                    >
                      <span>Sign in</span>
                      <ArrowRight className="w-3 h-3 stroke-[2.5]" aria-hidden="true" />
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Secure Session Guarantee */}
          <div className="flex items-center justify-center gap-2 mt-4 text-[11px] text-neutral-400 font-mono">
            <Shield className="w-3.5 h-3.5 text-neutral-400" aria-hidden="true" />
            <span>Encrypted session</span>
            <span>•</span>
            <span>Secure authentication</span>
          </div>
        </section>
      </main>

      {/* ================= BOTTOM FOOTER BAR ================= */}
      <footer className="w-full px-4 sm:px-6 md:px-12 py-4 flex items-center justify-between text-[10px] font-mono tracking-widest text-neutral-400 uppercase border-t border-white/[0.04] z-20">
        <div className="text-neutral-400">
          — IDEAS MOVE THE WORLD FORWARD.
        </div>

        <div className="flex items-center gap-2 text-neutral-300 font-medium">
          <span className="text-[11px]" aria-hidden="true">❖</span>
          <span>TECH NEWS TODAY</span>
        </div>
      </footer>
    </div>
  );
}
