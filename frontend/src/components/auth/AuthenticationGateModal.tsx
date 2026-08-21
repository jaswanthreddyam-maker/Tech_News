"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { GoogleLogin } from "@react-oauth/google";
import { Lock, Mail, User, ShieldCheck, Sparkles, X, ArrowRight, Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useAuthGate } from "@/hooks/useAuthGate";
import { useAppStore } from "@/store/useStore";
import { sessionManager } from "@/lib/session/sessionManager";
import { apiFetch } from "@/lib/api/client";
import { sanitizeReturnUrl } from "@/lib/auth/safeReturnUrl";

export function AuthenticationGateModal() {
  const router = useRouter();
  const { authGate, closeAuthGate, featureMeta } = useAuthGate();
  const { loginUser } = useAppStore();

  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!authGate.isOpen) {
    return null;
  }

  const handleAuthSuccess = (userData: any, accessToken: string) => {
    loginUser(userData, accessToken);
    closeAuthGate();
    if (authGate.returnUrl && typeof window !== "undefined") {
      const safeTarget = sanitizeReturnUrl(authGate.returnUrl);
      const current = window.location.pathname + window.location.search;
      if (safeTarget !== current && safeTarget !== "/") {
        router.push(safeTarget);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please fill in all required fields.");
      return;
    }
    if (mode === "signup" && !name.trim()) {
      setError("Please provide your name.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      if (mode === "login") {
        const data = await sessionManager.login({
          email: email.trim(),
          password,
        });
        handleAuthSuccess(data.user, data.access_token);
      } else {
        const data = await sessionManager.register({
          name: name.trim(),
          email: email.trim(),
          password,
        });
        handleAuthSuccess(data.user, data.access_token);
      }
    } catch (err: any) {
      setError(err?.message || "Authentication failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setError(null);
    setLoading(true);
    try {
      const data = await apiFetch<{ user: any; access_token: string }>("/auth/google", {
        method: "POST",
        body: JSON.stringify({ credential: credentialResponse.credential }),
      });
      handleAuthSuccess(data.user, data.access_token);
    } catch (err: any) {
      setError(err?.message || "Google sign-in failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const title = featureMeta?.title || "Authentication Required";
  const subtitle = featureMeta?.subtitle || "Sign in to unlock AI analysis, personalized bookmarks, and executive briefings.";
  const badge = featureMeta?.badge || "AUTHENTICATION GATE";

  return (
    <Dialog open={authGate.isOpen} onOpenChange={(open) => !open && closeAuthGate()}>
      <DialogContent className="sm:max-w-[440px] p-0 bg-[#0c0d0e]/95 backdrop-blur-2xl border border-white/10 text-foreground shadow-2xl rounded-3xl overflow-hidden z-[99999]">
        {/* Glow Header */}
        <div className="relative p-6 pb-4 border-b border-white/[0.08] bg-gradient-to-b from-primary/10 via-transparent to-transparent">
          <div className="flex items-center justify-between gap-3 mb-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-widest uppercase bg-primary/15 text-primary border border-primary/25">
              <Sparkles className="w-3 h-3 text-primary" />
              {badge}
            </span>
          </div>

          <DialogHeader className="text-left space-y-1.5">
            <DialogTitle className="text-xl font-bold tracking-tight text-white">
              {title}
            </DialogTitle>
            <DialogDescription className="text-xs sm:text-sm text-neutral-400 leading-relaxed">
              {subtitle}
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Form Body */}
        <div className="p-6 pt-4 space-y-5">
          {/* Mode Switcher */}
          <div className="grid grid-cols-2 p-1 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs font-semibold">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError(null);
              }}
              className={`py-1.5 rounded-lg transition-all ${
                mode === "login"
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("signup");
                setError(null);
              }}
              className={`py-1.5 rounded-lg transition-all ${
                mode === "signup"
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Google Sign-in */}
          <div className="flex flex-col items-center justify-center">
            <div className="w-full flex justify-center py-0.5">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError("Google Sign-In was cancelled or failed.")}
                theme="filled_black"
                shape="pill"
                size="large"
                text={mode === "login" ? "signin_with" : "signup_with"}
                width="100%"
              />
            </div>
            <div className="relative w-full flex items-center justify-center my-3">
              <div className="w-full border-t border-white/[0.08]" />
              <span className="absolute px-3 text-[11px] font-mono text-neutral-500 bg-[#0c0d0e] uppercase tracking-wider">
                or email
              </span>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs leading-relaxed">
              {error}
            </div>
          )}

          {/* Email / Password Form */}
          <form onSubmit={handleSubmit} className="space-y-3.5">
            {mode === "signup" && (
              <div className="space-y-1">
                <label htmlFor="auth-gate-name" className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider">Full Name</label>
                <div className="relative flex items-center">
                  <User className="absolute left-3 w-4 h-4 text-neutral-500" />
                  <input
                    id="auth-gate-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Alex Morgan"
                    className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-xs sm:text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-primary/60 transition-colors"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label htmlFor="auth-gate-email" className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider">Email Address</label>
              <div className="relative flex items-center">
                <Mail className="absolute left-3 w-4 h-4 text-neutral-500" />
                <input
                  id="auth-gate-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  required
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-xs sm:text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-primary/60 transition-colors"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label htmlFor="auth-gate-password" className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider">Password</label>
              <div className="relative flex items-center">
                <Lock className="absolute left-3 w-4 h-4 text-neutral-500" />
                <input
                  id="auth-gate-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-xs sm:text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-primary/60 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 hover:bg-primary/90 transition-all disabled:opacity-50 cursor-pointer shadow-lg shadow-primary/20"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin rounded-full" />
              ) : (
                <>
                  <span>{mode === "login" ? "Sign In & Continue" : "Create Account & Continue"}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Footer note */}
          <div className="pt-2 flex items-center justify-between text-xs text-neutral-500">
            <button
              type="button"
              onClick={closeAuthGate}
              className="hover:text-neutral-300 transition-colors cursor-pointer"
            >
              Continue reading as guest
            </button>
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-neutral-400" />
              Zero-Trust Encrypted
            </span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
