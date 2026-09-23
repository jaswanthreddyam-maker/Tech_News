"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

const API_BASE_URL = getApiBaseUrl();

type Step = "email" | "code" | "password";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [step, setStep] = useState<Step>("email");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Step 1: Email
  const [email, setEmail] = useState("");

  // Step 2: OTP Code
  const [code, setCode] = useState("");

  // Step 3: New Password
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Password validation
  const passHasMinLength = newPassword.length >= 8;
  const passHasUppercase = /[A-Z]/.test(newPassword);
  const passHasLowercase = /[a-z]/.test(newPassword);
  const passHasNumber = /[0-9]/.test(newPassword);
  const passMatchesConfirm = newPassword === confirmPassword && confirmPassword.length > 0;
  const isPasswordValid = passHasMinLength && passHasUppercase && passHasLowercase && passHasNumber;

  // Step 1: Request OTP
  const handleRequestCode = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedEmail = email.trim().toLowerCase();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: trimmedEmail }),
      });

      const payload = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(payload?.detail || "Unable to send reset code. Please try again.");
        return;
      }

      setStep("code");
    } catch {
      setError("Network error. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify OTP code format and proceed to password
  const handleVerifyCode = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedCode = code.trim();
    if (trimmedCode.length !== 6 || !/^\d{6}$/.test(trimmedCode)) {
      setError("Please enter a valid 6-digit code.");
      return;
    }

    setStep("password");
  };

  // Step 3: Reset password
  const handleResetPassword = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isPasswordValid) {
      setError("Password does not meet the required security criteria.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          code: code.trim(),
          new_password: newPassword,
        }),
      });

      const payload = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(payload?.detail || "Unable to reset password. Please try again.");
        return;
      }

      setSuccessMessage("Password reset successfully! Redirecting to sign in...");
      setTimeout(() => {
        router.push("/login");
      }, 2500);
    } catch {
      setError("Network error. Please check your connection and try again.");
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

  const stepTitles: Record<Step, string> = {
    email: "Reset Password",
    code: "Enter Verification Code",
    password: "Create New Password",
  };

  const stepDescriptions: Record<Step, string> = {
    email: "Enter the email address associated with your account.",
    code: `A 6-digit verification code has been sent to ${email}`,
    password: "Choose a strong password for your account.",
  };

  return (
    <div className="min-h-screen bg-[#080808] flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Subtle background grid */}
      <div className="absolute inset-0 border-grid opacity-[0.03]" />

      {/* System status bar */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-neutral-950 border-b border-[#1a1a1a] py-1.5 px-4">
        <div className="flex items-center justify-center gap-2 font-mono text-[9px] tracking-[0.25em] uppercase text-neutral-400">
          <span className="h-1.5 w-1.5 bg-emerald-500 animate-pulse inline-block" />
          <span>TECH NEWS TODAY &bull; PASSWORD RECOVERY NODE</span>
        </div>
      </div>

      {/* Main card */}
      <div className="w-full max-w-md relative z-10">
        {/* Logo header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold tracking-tighter text-white font-sans uppercase">
            TECH NEWS TODAY
          </h1>
          <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-[#888] mt-2">
            Account Recovery Protocol
          </p>
        </div>

        {/* Progress indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {(["email", "code", "password"] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-2 h-2 transition-colors duration-300 ${
                  step === s
                    ? "bg-white"
                    : (["email", "code", "password"] as Step[]).indexOf(step) > i
                    ? "bg-emerald-500"
                    : "bg-[#333]"
                }`}
              />
              {i < 2 && (
                <div
                  className={`w-8 h-px transition-colors duration-300 ${
                    (["email", "code", "password"] as Step[]).indexOf(step) > i
                      ? "bg-emerald-500/50"
                      : "bg-[#222]"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div
          className={`border bg-[#0c0c0c] p-6 transition-colors duration-300 ${
            error ? "border-red-500/60" : "border-[#1a1a1a]"
          }`}
        >
          {/* Step title */}
          <div className="mb-5">
            <h2 className="text-lg font-bold text-white tracking-tight">
              {stepTitles[step]}
            </h2>
            <p className="font-mono text-[10px] tracking-wider text-[#888] mt-1.5 leading-relaxed">
              {stepDescriptions[step]}
            </p>
          </div>

          {/* Success Message */}
          {successMessage && (
            <div className="mb-4 border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 flex items-start gap-2">
              <svg
                className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <span className="font-mono text-[10px] text-emerald-400 leading-relaxed">
                {successMessage}
              </span>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="mb-4 border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-start gap-2">
              <svg
                className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span className="font-mono text-[10px] text-red-400 leading-relaxed">
                {error}
              </span>
            </div>
          )}

          {/* Step 1: Email Form */}
          {step === "email" && (
            <form onSubmit={handleRequestCode} className="space-y-4">
              <div>
                <label
                  htmlFor="reset-email"
                  className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
                >
                  Email Address
                </label>
                <input
                  id="reset-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@technews.today"
                  className="w-full bg-[#080808] border border-[#1a1a1a] px-3 py-2.5 font-mono text-[12px] text-white placeholder-neutral-600 focus:outline-none focus:border-white transition-colors"
                />
              </div>

              <button
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
                    <span>SENDING CODE</span>
                  </>
                ) : (
                  <span>SEND RESET CODE</span>
                )}
              </button>
            </form>
          )}

          {/* Step 2: OTP Code Form */}
          {step === "code" && (
            <form onSubmit={handleVerifyCode} className="space-y-4">
              <div>
                <label
                  htmlFor="reset-code"
                  className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
                >
                  6-Digit Verification Code
                </label>
                <input
                  id="reset-code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(e) => {
                    const val = e.target.value.replace(/[^0-9]/g, "");
                    setCode(val);
                  }}
                  placeholder="000000"
                  className="w-full bg-[#080808] border border-[#1a1a1a] px-3 py-3 font-mono text-[20px] text-white text-center tracking-[0.5em] placeholder-neutral-600 focus:outline-none focus:border-white transition-colors"
                />
              </div>

              <div className="font-mono text-[9px] tracking-wider text-[#555] flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 bg-amber-500/60 inline-block" />
                <span>Code expires in 15 minutes</span>
              </div>

              <button
                type="submit"
                disabled={code.length !== 6}
                className="w-full bg-white text-black font-mono text-[11px] uppercase tracking-[0.2em] py-3 hover:bg-neutral-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <span>VERIFY CODE</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("email");
                  setCode("");
                  setError(null);
                }}
                className="w-full font-mono text-[10px] tracking-wider text-[#666] hover:text-white uppercase transition-colors py-1"
              >
                &larr; Back to email
              </button>
            </form>
          )}

          {/* Step 3: New Password Form */}
          {step === "password" && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              {/* New Password */}
              <div>
                <label
                  htmlFor="new-password"
                  className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
                >
                  New Password
                </label>
                <div className="relative">
                  <input
                    id="new-password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;"
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

                {/* Password criteria */}
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
                  htmlFor="confirm-new-password"
                  className="block font-mono text-[9px] tracking-widest uppercase text-[#888] mb-1.5"
                >
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    id="confirm-new-password"
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;"
                    className={`w-full bg-[#080808] border px-3 py-2.5 font-mono text-[12px] text-white placeholder-neutral-600 focus:outline-none transition-colors ${
                      confirmPassword.length > 0
                        ? passMatchesConfirm
                          ? "border-emerald-500/40 focus:border-emerald-500"
                          : "border-red-500/40 focus:border-red-500"
                        : "border-[#1a1a1a] focus:border-white"
                    }`}
                  />
                  {confirmPassword.length > 0 && (
                    <span
                      className={`absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[7px] uppercase font-bold tracking-wider ${
                        passMatchesConfirm ? "text-emerald-500" : "text-red-500"
                      }`}
                    >
                      {passMatchesConfirm ? "MATCH" : "MISMATCH"}
                    </span>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !isPasswordValid || !passMatchesConfirm}
                className="w-full bg-white text-black font-mono text-[11px] uppercase tracking-[0.2em] py-3 hover:bg-neutral-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                    </svg>
                    <span>RESETTING PASSWORD</span>
                  </>
                ) : (
                  <span>RESET PASSWORD</span>
                )}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("code");
                  setNewPassword("");
                  setConfirmPassword("");
                  setError(null);
                }}
                className="w-full font-mono text-[10px] tracking-wider text-[#666] hover:text-white uppercase transition-colors py-1"
              >
                &larr; Back to code entry
              </button>
            </form>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-[#1a1a1a]" />
            <span className="font-mono text-[9px] text-[#555] tracking-widest">OR</span>
            <div className="flex-1 h-px bg-[#1a1a1a]" />
          </div>

          {/* Back to login */}
          <div className="text-center font-mono text-[10px] tracking-wider text-[#666] select-none">
            Remember your password?{" "}
            <Link
              href="/login"
              className="text-white hover:underline uppercase font-bold transition-colors"
            >
              Sign In
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
