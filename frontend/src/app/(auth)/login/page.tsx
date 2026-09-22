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

const FEATURED_CARDS = [
  {
    id: "ai-card",
    category: "ARTIFICIAL INTELLIGENCE",
    time: "2H AGO",
    title: "Next-generation AI models reshape the enterprise landscape",
    description:
      "From autonomous agents to multimodal systems, a new wave of AI is changing how work gets done.",
    image: "/images/login/card-ai.jpg",
  },
  {
    id: "nvidia-card",
    category: "TECH INDUSTRY",
    time: "4H AGO",
    title: "NVIDIA signals next chapter in accelerated computing",
    description:
      "New infrastructure, broader partnerships, and a growing developer ecosystem point to an AI-native future.",
    image: "/images/login/card-nvidia.jpg",
  },
  {
    id: "security-card",
    category: "CYBERSECURITY",
    time: "6H AGO",
    title: "Major cloud providers unite on new security standards",
    description:
      "A coordinated push aims to raise the bar for AI-era infrastructure security.",
    image: "/images/login/card-security.jpg",
  },
  {
    id: "space-card",
    category: "SPACE & SCIENCE",
    time: "8H AGO",
    title: "Private space companies accelerate global connectivity",
    description:
      "New launches and tighter regulation could reshape the next decade of internet access.",
    image: "/images/login/card-space.jpg",
  },
];

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
      {/* Background Graphic: Realistic Space Earth Globe & Starfield */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <Image
          src="/images/login/globe-bg.jpg"
          alt="Orbital intelligence background"
          fill
          priority
          sizes="100vw"
          className="object-cover object-[70%_center] lg:object-[68%_center]"
        />
      </div>

      {/* ================= TOP HEADER BAR ================= */}
      <header className="w-full px-6 md:px-12 py-5 flex items-center justify-between z-20 text-[11px] font-mono tracking-widest uppercase">
        {/* Left: Global Desk Online indicator (Clean Monochrome) */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.85)] animate-pulse" />
            <span className="text-neutral-200 font-semibold tracking-[0.2em]">
              GLOBAL DESK
            </span>
            <span className="text-neutral-600">•</span>
            <span className="text-neutral-400 font-medium">ONLINE</span>
          </div>

          <div className="hidden sm:flex items-center gap-2 pl-4 text-neutral-600">
            <span className="w-16 h-[1px] bg-neutral-800" />
            <span className="text-[10px] text-neutral-500">+</span>
          </div>
        </div>

        {/* Right: Technical Pillar Header */}
        <div className="text-right text-neutral-500 text-[9px] font-mono leading-[1.35] tracking-[0.2em] hidden sm:block">
          <div className="text-neutral-300 font-semibold">+ TECHNOLOGY</div>
          <div>PEOPLE</div>
          <div className="text-neutral-400">A BRIGHTER TOMORROW</div>
        </div>
      </header>

      {/* ================= MAIN CONTENT ================= */}
      <main className="w-full max-w-[1720px] mx-auto px-6 md:px-12 py-2 lg:py-4 flex-1 flex flex-col lg:flex-row items-center lg:items-center justify-between gap-10 xl:gap-14 z-10">
        {/* LEFT COLUMN: HERO INTELLIGENCE & 3D OVERLAPPING CARDS */}
        <section className="w-full lg:max-w-[58%] xl:max-w-[62%] flex flex-col justify-center overflow-visible">
          {/* Eyebrow & Brand Headings */}
          <div className="flex flex-col mb-6 lg:mb-7">
            <p className="font-mono text-[10px] sm:text-[11px] tracking-[0.32em] text-neutral-400 uppercase font-medium mb-3">
              THE DAILY TECHNOLOGY INTELLIGENCE
            </p>

            <h1 className="text-4xl sm:text-5xl xl:text-6xl font-black tracking-tight text-white uppercase font-sans leading-[1.05]">
              TECH NEWS TODAY
            </h1>

            <p className="text-lg sm:text-xl lg:text-2xl text-neutral-300 font-light mt-3 leading-relaxed max-w-2xl">
              Your personal gateway to the technology that matters.
            </p>

            {/* Pillar Subtitle Strip */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[9px] sm:text-[10px] font-mono tracking-[0.2em] text-neutral-500 uppercase mt-4">
              <span>BREAKING NEWS</span>
              <span className="text-neutral-700">/</span>
              <span>DEEP ANALYSIS</span>
              <span className="text-neutral-700">/</span>
              <span>EXPERT PERSPECTIVE</span>
              <span className="text-neutral-700">/</span>
              <span>A MORE INFORMED TOMORROW</span>
            </div>
          </div>

          {/* Micro Tech Telemetry Text Overlay (matching image) */}
          <div className="flex justify-end pr-8 mb-2 hidden lg:flex">
            <div className="text-right text-[9px] font-mono tracking-[0.22em] text-neutral-500 leading-tight uppercase">
              <div>REAL NEWS</div>
              <div>REAL PEOPLE</div>
              <div>REAL IMPACT</div>
            </div>
          </div>

          {/* 4 3D EXTRUDED CARDS STANDING BEHIND EACH OTHER */}
          <div className="w-full [perspective:1400px] py-4 overflow-visible">
            <div
              className="flex flex-row items-center w-full overflow-x-auto lg:overflow-visible pb-4 lg:pb-0 scrollbar-none"
              style={{ transformStyle: "preserve-3d" }}
            >
              {FEATURED_CARDS.map((card, idx) => {
                // Stacking order: Card 1 is in front (40), Card 4 is furthest back (10)
                const zIndex = 40 - idx * 10;
                return (
                  <article
                    key={card.id}
                    className={`group relative shrink-0 w-[200px] sm:w-[215px] xl:w-[230px] h-[335px] sm:h-[345px] xl:h-[355px] cursor-pointer select-none transition-all duration-500 ${
                      idx > 0 ? "-ml-3 sm:-ml-3.5 xl:-ml-4" : ""
                    } hover:!z-50 hover:-translate-y-3 hover:translate-x-1`}
                    style={{
                      zIndex,
                      transform:
                        "rotateY(-11deg) rotateX(1deg) rotateZ(0deg)",
                      transformStyle: "preserve-3d",
                    }}
                  >
                    {/* 3D Physical Extruded Slab Back Plate (from HeroMediaCard) */}
                    <div
                      className="absolute inset-0 rounded-2xl bg-neutral-950 border border-white/20 shadow-[0_30px_60px_rgba(0,0,0,0.95)] pointer-events-none"
                      style={{
                        transform: "translateZ(-14px)",
                      }}
                    />

                    {/* 3D Slab Thickness Ring Frame (from HeroMediaCard) */}
                    <div
                      className="absolute inset-0 rounded-2xl border border-white/10 bg-white/[0.03] pointer-events-none"
                      style={{
                        transform: "translateZ(-7px)",
                      }}
                    />

                    {/* Front Face Glass Card Container (from HeroMediaCard) */}
                    <div
                      className={`relative w-full h-full flex flex-col p-4 bg-black rounded-2xl overflow-hidden border transition-all duration-500 cubic-bezier(0.4, 0, 0.2, 1) ${
                        idx === 0
                          ? "border-white/45 ring-1 ring-white/30 shadow-[0_25px_50px_-10px_rgba(0,0,0,0.95),0_0_30px_rgba(255,255,255,0.15),inset_0_1px_1px_rgba(255,255,255,0.5)] group-hover:border-white/70 group-hover:shadow-[0_30px_60px_-10px_rgba(0,0,0,0.95),0_0_40px_rgba(255,255,255,0.25)]"
                          : "border-white/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_15px_30px_rgba(0,0,0,0.8)] opacity-95 group-hover:opacity-100 group-hover:border-white/45 group-hover:shadow-[0_0_28px_rgba(255,255,255,0.2)]"
                      }`}
                      style={{
                        transformStyle: "preserve-3d",
                      }}
                    >
                      {/* Layer 2: Photorealistic Specular Sheen (from HeroMediaCard) */}
                      <div
                        className="absolute inset-0 pointer-events-none z-20 mix-blend-overlay transition-opacity duration-500 opacity-40 group-hover:opacity-85"
                        style={{
                          background:
                            "linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.12) 25%, transparent 55%, rgba(0,0,0,0.3) 100%)",
                        }}
                      />

                      {/* Layer 3: Photorealistic Optical Glare Sweep (from HeroMediaCard) */}
                      <div className="absolute inset-0 pointer-events-none z-25 overflow-hidden">
                        <div
                          className="absolute -top-[50%] -bottom-[50%] -left-[160%] w-[320%] bg-[linear-gradient(115deg,transparent_40%,rgba(255,255,255,0.03)_47%,rgba(255,255,255,0.25)_50%,rgba(255,255,255,0.03)_53%,transparent_60%)] group-hover:translate-x-[70%] transition-transform duration-[1100ms] cubic-bezier(0.16,1,0.3,1)"
                          style={{ willChange: "transform" }}
                        />
                      </div>

                      {/* Layer 4: Fresnel Top-Edge Specular Catch (from HeroMediaCard) */}
                      <div className="absolute inset-0 pointer-events-none z-30 rounded-2xl border border-white/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.45),inset_0_-1px_1px_rgba(0,0,0,0.6)] group-hover:border-white/40 transition-colors duration-500" />

                      {/* Header Tag + Time (Strict single-line across all cards) */}
                      <div className="flex items-center justify-between text-[8.5px] sm:text-[9px] font-mono mb-2.5 relative z-10 shrink-0 h-4">
                        <span className="text-white font-bold uppercase tracking-[0.08em] sm:tracking-[0.1em] whitespace-nowrap overflow-hidden text-ellipsis drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
                          {card.category}
                        </span>
                        <span className="text-neutral-500 uppercase tracking-widest text-[8px] sm:text-[8.5px] shrink-0 ml-1 font-medium">
                          {card.time}
                        </span>
                      </div>

                      {/* Card Thumbnail Image (Full Color Media) */}
                      <div className="relative aspect-[16/11] w-full shrink-0 rounded-xl overflow-hidden bg-black mb-2.5 border border-white/[0.08] shadow-inner relative z-10">
                        <Image
                          src={card.image}
                          alt={card.title}
                          fill
                          sizes="(max-width: 768px) 100vw, 25vw"
                          className="object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent pointer-events-none" />
                      </div>

                      {/* Headline Title (Fixed 2-line height across all cards) */}
                      <h2 className="text-[11.5px] xl:text-[12px] font-bold text-white leading-snug line-clamp-2 h-[34px] sm:h-[36px] shrink-0 group-hover:text-neutral-100 transition-colors relative z-10">
                        {card.title}
                      </h2>

                      {/* Narrative Excerpt (Uniform fit) */}
                      <p className="text-[9px] xl:text-[9.5px] text-neutral-400 font-normal leading-[1.38] line-clamp-3 overflow-hidden mt-1 relative z-10">
                        {card.description}
                      </p>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: LOGIN FORM CARD (Pure Black Glassmorphic) */}
        <section className="w-full lg:w-[440px] xl:w-[470px] shrink-0">
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
