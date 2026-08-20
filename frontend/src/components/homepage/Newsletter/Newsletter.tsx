"use client";

import { useState } from "react";
import { Mail, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { m } from "framer-motion";
import { getApiBaseUrl } from "@/lib/api/getApiBaseUrl";

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
      const baseUrl = typeof window !== "undefined" ? "" : getApiBaseUrl();
      
      // Subscribe directly to the Daily AI Briefing delivery engine
      const briefingRes = await fetch(`${baseUrl}/api/v1/briefing/preferences`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          enabled: true,
          delivery_time: "08:00",
          timezone: (typeof Intl !== "undefined" && Intl.DateTimeFormat().resolvedOptions().timeZone) || "Asia/Kolkata",
          story_count: 5,
          topics: ["artificial-intelligence", "technology", "cybersecurity"]
        })
      });

      // Best-effort sync with newsletter table
      fetch(`${baseUrl}/api/v1/newsletter/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      }).catch(() => {});

      if (!briefingRes.ok) {
        const data = await briefingRes.json().catch(() => ({}));
        throw new Error(data.detail || data.message || "Subscription failed");
      }

      setStatus("success");
      setEmail("");
    } catch (err: any) {
      setStatus("error");
      setErrorMessage(err.message || "Unable to subscribe. Please try again.");
    }
  };

  return (
    <section className="my-16 w-full flex justify-center relative max-w-lg mx-auto px-4">
      <div className="w-full">
        <m.div 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={{
            hidden: { clipPath: "circle(30px at center)" },
            visible: { 
              clipPath: "circle(150% at center)", 
              transition: { duration: 2.0, ease: [0.22, 1, 0.36, 1] } 
            }
          }}
          className="relative w-full rounded-3xl border-[3px] reading-desk-card-glow overflow-hidden bg-[#0D0D0D]/90 backdrop-blur-xl shadow-2xl"
        >
          {/* Ambient glow */}
          <div className="absolute inset-0 bg-gradient-to-b from-white/[0.04] to-transparent pointer-events-none" />
          
          <m.div
            variants={{
              hidden: { opacity: 0 },
              visible: { opacity: 1, transition: { delay: 1.2, duration: 0.8, ease: "easeOut" } }
            }}
            className="relative z-10 w-full flex flex-col items-center pt-10 px-8 pb-10"
          >
            <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mb-4 shrink-0">
              {status === 'success' ? (
                <CheckCircle className="w-6 h-6 text-primary" />
              ) : (
                <Mail className="w-6 h-6 text-primary" />
              )}
            </div>
            
            <h2 className="font-sans font-bold text-3xl text-center text-foreground">Daily AI Briefing</h2>
            <p className="text-muted-foreground/80 font-mono text-sm mt-3 mb-8 text-center">
              5 minute read. Every morning. Zero spam.
            </p>
            
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 w-full max-w-md mx-auto">
              {status === "success" ? (
                <div className="bg-primary/10 border border-primary/30 text-primary rounded-[14px] p-3 flex items-center justify-center gap-2 font-mono text-xs w-full">
                  <CheckCircle className="w-4 h-4" />
                  <span>Subscribed Successfully!</span>
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
                    className="px-4 py-2.5 font-mono text-sm transition-all focus:outline-none disabled:opacity-50 placeholder:text-muted-foreground/50 bg-black/50 border border-white/15 rounded-xl text-foreground focus:border-primary focus:ring-1 focus:ring-primary w-full flex-1"
                  />
                  <button 
                    type="submit" 
                    disabled={status === "loading" || !email}
                    className="font-bold disabled:opacity-50 flex items-center justify-center bg-foreground text-background hover:bg-white/90 active:scale-[0.98] rounded-xl px-6 h-[44px] transition-all whitespace-nowrap"
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
          </m.div>
        </m.div>
      </div>
    </section>
  );
}
