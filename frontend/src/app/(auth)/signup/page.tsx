"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAppStore } from "@/store/useStore";
import { canAccessAdmin } from "@/lib/auth/permissions";
import { sessionManager } from "@/lib/session/sessionManager";

export default function SignupPage() {
  const router = useRouter();
  const { user, loginUser } = useAppStore();

  // Form Fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);

  // Layout & UI States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDuplicateEmail, setIsDuplicateEmail] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [showWelcomeToast, setShowWelcomeToast] = useState(false);
  const [progressWidth, setProgressWidth] = useState(0);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Redirect if already logged in
  useEffect(() => {
    if (mounted && user) {
      if (canAccessAdmin(user)) {
        router.push("/admin");
      } else {
        router.push("/");
      }
    }
  }, [mounted, user, router]);

  // Live password validation criteria checks
  const passHasMinLength = password.length >= 8;
  const passHasUppercase = /[A-Z]/.test(password);
  const passHasLowercase = /[a-z]/.test(password);
  const passHasNumber = /[0-9]/.test(password);
  const passMatchesConfirm = password === confirmPassword && confirmPassword.length > 0;
  
  // All password validations must pass
  const isPasswordValid = passHasMinLength && passHasUppercase && passHasLowercase && passHasNumber;

  const handleSignup = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsDuplicateEmail(false);

    // Frontend Validations
    if (name.trim().length < 2) {
      setError("Full Name must be at least 2 characters long.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }

    if (!isPasswordValid) {
      setError("Password does not meet the required security criteria.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Password and Confirm Password fields must match.");
      return;
    }

    if (!agreeTerms) {
      setError("You must agree to the Terms of Service to create an account.");
      return;
    }

    setLoading(true);

    try {
      // POST /auth/register
      const data = await sessionManager.register({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password: password,
      });

      // Session binding (Auto-login)
      loginUser(data.user, data.access_token);
      
      // Trigger Welcome Toast with progress animation and delayed redirect
      setShowWelcomeToast(true);
      setTimeout(() => setProgressWidth(100), 50);
      setTimeout(() => {
        router.push("/");
      }, 2500);
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes("Email already registered")) {
        setError("Email already registered.");
        setIsDuplicateEmail(true);
      } else if (err.status === 429) {
        setError("Too many registration attempts. Please wait a minute.");
      } else {
        setError(err.message || "Registration failed. Try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#080808] flex items-center justify-center">
        <div className="w-6 h-6 border border-white/20 border-t-white animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080808] flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Subtle background grid */}
      <div className="absolute inset-0 border-grid opacity-[0.03]" />

      {/* System status bar */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-neutral-950 border-b border-[#1a1a1a] py-1.5 px-4">
        <div className="flex items-center justify-center gap-2 font-mono text-[9px] tracking-[0.25em] uppercase text-neutral-400">
          <span className="h-1.5 w-1.5 bg-emerald-500 animate-pulse inline-block" />
          <span>TECH NEWS TODAY • REGISTER OPERATION NODE</span>
        </div>
      </div>

      {/* Signup card */}
      <div className="w-full max-w-md relative z-10">
        {/* Logo header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold tracking-tighter text-white font-sans uppercase">
            TECH NEWS TODAY
          </h1>
          <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-[#888] mt-2">
            Create Operations Account
          </p>
        </div>

        {/* Main card */}
        <div
          className={`border bg-[#0c0c0c] p-6 transition-colors duration-300 ${
            error ? "border-red-500/60" : "border-[#1a1a1a]"
          }`}
        >
          {/* Error banner with duplicate email specific handler */}
          {error && (
            <div className="mb-4 border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-start gap-2">
              <svg className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <div className="font-mono text-[10px] text-red-400 leading-relaxed">
                {isDuplicateEmail ? (
                  <span>
                    Email already registered.{" "}
                    <Link href="/login" className="text-white underline font-bold">
                      [Login Instead]
                    </Link>
                  </span>
                ) : (
                  <span>{error}</span>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSignup} className="space-y-4">
            {/* Full Name */}
            <div>
              <label
                htmlFor="signup-name"
                className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
              >
                Full Name
              </label>
              <input
                id="signup-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Operator Name"
                className="w-full bg-[#080808] border border-[#1a1a1a] px-3 py-2.5 font-mono text-[12px] text-white placeholder-neutral-600 focus:outline-none focus:border-white transition-colors"
              />
            </div>

            {/* Email Address */}
            <div>
              <label
                htmlFor="signup-email"
                className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
              >
                Email Address
              </label>
              <input
                id="signup-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@technews.today"
                className="w-full bg-[#080808] border border-[#1a1a1a] px-3 py-2.5 font-mono text-[12px] text-white placeholder-neutral-600 focus:outline-none focus:border-white transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="signup-password"
                className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="signup-password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[#080808] border border-[#1a1a1a] px-3 py-2.5 pr-16 font-mono text-[12px] text-white placeholder-neutral-600 focus:outline-none focus:border-white transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[8px] tracking-widest uppercase text-[#555] hover:text-white transition-colors"
                >
                  {showPassword ? "HIDE" : "SHOW"}
                </button>
              </div>

              {/* Password Dynamic Live Validations */}
              <div className="mt-2 border border-[#1a1a1a] bg-[#080808] p-2 space-y-1 font-mono text-[8px] tracking-wider text-[#555]">
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${passHasMinLength ? "bg-emerald-500 animate-pulse" : "bg-[#333]"}`} />
                  <span className={passHasMinLength ? "text-neutral-300" : "text-[#555]"}>MINIMUM 8 CHARACTERS</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${passHasUppercase ? "bg-emerald-500 animate-pulse" : "bg-[#333]"}`} />
                  <span className={passHasUppercase ? "text-neutral-300" : "text-[#555]"}>ONE UPPERCASE LETTER</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${passHasLowercase ? "bg-emerald-500 animate-pulse" : "bg-[#333]"}`} />
                  <span className={passHasLowercase ? "text-neutral-300" : "text-[#555]"}>ONE LOWERCASE LETTER</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${passHasNumber ? "bg-emerald-500 animate-pulse" : "bg-[#333]"}`} />
                  <span className={passHasNumber ? "text-neutral-300" : "text-[#555]"}>ONE NUMBER</span>
                </div>
              </div>
            </div>

            {/* Confirm Password */}
            <div>
              <label
                htmlFor="signup-confirm-password"
                className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
              >
                Confirm Password
              </label>
              <div className="relative">
                <input
                  id="signup-confirm-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className={`w-full bg-[#080808] border px-3 py-2.5 font-mono text-[12px] text-white placeholder-neutral-600 focus:outline-none transition-colors ${
                    confirmPassword.length > 0
                      ? passMatchesConfirm
                        ? "border-emerald-500/40 focus:border-emerald-500"
                        : "border-red-500/40 focus:border-red-500"
                      : "border-[#1a1a1a] focus:border-white"
                  }`}
                />
                {confirmPassword.length > 0 && (
                  <span className={`absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[7px] uppercase font-bold tracking-wider ${passMatchesConfirm ? "text-emerald-500" : "text-red-500"}`}>
                    {passMatchesConfirm ? "MATCH" : "MISMATCH"}
                  </span>
                )}
              </div>
            </div>

            {/* Terms of Service Checkbox */}
            <div className="flex items-start">
              <label className="flex items-start gap-2.5 cursor-pointer group" htmlFor="signup-terms">
                <div className="relative mt-0.5 shrink-0">
                  <input
                    id="signup-terms"
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    className={`w-3.5 h-3.5 border transition-colors ${
                      agreeTerms
                        ? "bg-white border-white"
                        : "border-[#333] group-hover:border-[#555]"
                    }`}
                  >
                    {agreeTerms && (
                      <svg className="w-3.5 h-3.5 text-black" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                </div>
                <span className="font-mono text-[9px] tracking-wider uppercase text-[#888] group-hover:text-white transition-colors leading-tight select-none">
                  I agree to the Terms of Service & transmission protocols
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              id="signup-submit"
              type="submit"
              disabled={loading}
              className="w-full bg-white text-black font-mono text-[11px] uppercase tracking-[0.2em] py-3 hover:bg-neutral-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  <span>CREATING ACCOUNT</span>
                </>
              ) : (
                <span>CREATE ACCOUNT</span>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-[#1a1a1a]" />
            <span className="font-mono text-[9px] text-[#555] tracking-widest">OR</span>
            <div className="flex-1 h-px bg-[#1a1a1a]" />
          </div>

          {/* Quick pivot to login */}
          <div className="text-center font-mono text-[10px] tracking-wider text-[#666] select-none">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-white hover:underline uppercase font-bold transition-colors"
            >
              Login
            </Link>
          </div>
        </div>

        {/* Footer system status */}
        <div className="mt-6 flex items-center justify-center gap-2">
          <span className="h-1.5 w-1.5 bg-emerald-500 inline-block" />
          <span className="font-mono text-[9px] tracking-[0.2em] uppercase text-[#555]">
            System Status: Operational
          </span>
        </div>
      </div>
    </div>
  );
}
