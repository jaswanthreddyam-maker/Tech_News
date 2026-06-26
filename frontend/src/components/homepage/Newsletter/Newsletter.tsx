"use client";

import { useState } from "react";
import { Mail, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Reveal } from "@/components/animations/Reveal";

export function Newsletter() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setStatus("loading");
    setErrorMessage("");

    try {
      const res = await fetch("/api/v1/newsletter/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Subscription failed");
      }

      setStatus("success");
      setEmail("");
    } catch (err: any) {
      setStatus("error");
      setErrorMessage(err.message || "Something went wrong.");
    }
  };

  return (
    <section className="my-16 w-full flex justify-center relative max-w-lg mx-auto">
      <Reveal className="w-full">
        <div 
          className="relative w-full rounded-[28px] border border-[#E9D8C7] overflow-hidden"
          style={{
            background: "linear-gradient(180deg, #FFF7EF 0%, #FDF1E5 100%)",
            boxShadow: "0 12px 35px rgba(0,0,0,0.06)"
          }}
        >
          {/* Noise overlay for texture */}
          <div 
            className="absolute inset-0 mix-blend-multiply pointer-events-none rounded-[inherit]"
            style={{
              backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")",
              opacity: 0.025
            }}
          />
          
          <div className="relative z-10 w-full flex flex-col items-center pt-10 px-8 pb-10">
            <div className="w-14 h-14 rounded-full bg-[#7A5C3E]/10 flex items-center justify-center mb-4 shrink-0">
              {status === 'success' ? (
                <CheckCircle className="w-6 h-6 text-[#7A5C3E]" />
              ) : (
                <Mail className="w-6 h-6 text-[#7A5C3E]" />
              )}
            </div>
            
            <h2 className="font-serif font-bold text-3xl text-center text-[#1B1B1B]">Daily AI Briefing</h2>
            <p className="text-[#6B7280] font-mono text-sm mt-3 mb-8 text-center">
              5 minute read. Every morning. No spam.
            </p>
            
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 w-full max-w-md mx-auto">
              {status === "success" ? (
                <div className="bg-[#FFF7EF] border border-[#E9D8C7] rounded-[14px] p-3 flex items-center justify-center gap-2 font-mono text-xs w-full" style={{ color: "#7A5C3E" }}>
                  <CheckCircle className="w-4 h-4" />
                  <span>Confirmed!</span>
                </div>
              ) : (
                <>
                  <input 
                    type="email" 
                    required
                    placeholder="agent@network.com" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={status === "loading"}
                    className="px-4 py-2.5 font-mono text-sm transition-all focus:outline-none disabled:opacity-50 placeholder:text-[#9CA3AF] focus:border-[#B88952] focus:shadow-[0_0_0_4px_rgba(184,137,82,0.12)] w-full flex-1"
                    style={{
                      background: "#FFFFFF",
                      border: "1px solid #E4D6C7",
                      borderRadius: "12px",
                      color: "#1B1B1B"
                    }}
                  />
                  <button 
                    type="submit" 
                    disabled={status === "loading" || !email}
                    className="font-bold disabled:opacity-50 flex items-center justify-center hover:bg-[#2B2B2B] active:scale-[0.98]"
                    style={{
                      background: "#1F1F1F",
                      color: "#FFFFFF",
                      borderRadius: "12px",
                      padding: "0 24px",
                      height: "44px",
                      transition: "250ms ease",
                      whiteSpace: "nowrap"
                    }}
                  >
                    {status === "loading" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Subscribe"}
                  </button>
                </>
              )}
            </form>
            
            {status === "error" && (
              <div className="text-red-500 flex items-center justify-center gap-1.5 font-mono text-xs mt-4 w-full">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>
        </div>
      </Reveal>
    </section>
  );
}
