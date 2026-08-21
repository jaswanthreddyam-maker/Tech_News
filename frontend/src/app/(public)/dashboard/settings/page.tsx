"use client";

import React, { useState, useEffect } from "react";
import { Container } from "@/components/layout/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import {
  Eye, Shield, User, Mail, Send, CheckCircle2,
  ChevronDown, ChevronUp, Sparkles, Clock, AlertCircle, MailCheck,
} from "lucide-react";
import {
  getBriefingPreferences,
  updateBriefingPreferences,
  sendTestBriefing,
  sendVerificationEmail,
} from "@/lib/api/briefing";
import { useAppStore } from "@/store/useStore";

const AVAILABLE_TOPICS = [
  { id: "artificial-intelligence", label: "AI & Neural Systems" },
  { id: "technology", label: "General Technology" },
  { id: "cybersecurity", label: "Cybersecurity" },
  { id: "hardware", label: "Hardware & Devices" },
  { id: "startups-and-business", label: "Startups & VC" },
  { id: "science", label: "Science & Quantum" },
];

function formatDeliveryTime(isoString?: string | null): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "—";
  }
}

export default function SettingsPage() {
  const { user } = useAppStore();
  const [enabled, setEnabled] = useState(false);
  const [email, setEmail] = useState(user?.email || "");
  const [emailVerified, setEmailVerified] = useState(false);
  const [deliveryTime, setDeliveryTime] = useState("08:00");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [storyCount, setStoryCount] = useState(5);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([
    "artificial-intelligence",
    "technology",
    "cybersecurity",
  ]);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [isSendingVerification, setIsSendingVerification] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [lastTelemetry, setLastTelemetry] = useState<{
    delivered_at?: string | null;
    status?: string;
    stories_count?: number;
  } | null>(null);

  useEffect(() => {
    if (user?.email && !email) {
      setEmail(user.email);
    }
  }, [user?.email, email]);

  // Load preferences on mount
  useEffect(() => {
    async function loadData() {
      try {
        const pref = await getBriefingPreferences(user?.email || undefined);
        if (pref) {
          setEnabled(pref.enabled);
          if (pref.email) setEmail(pref.email);
          setEmailVerified(pref.email_verified);
          setDeliveryTime(pref.delivery_time || "08:00");
          setTimezone(pref.timezone || "Asia/Kolkata");
          setStoryCount(pref.story_count || 5);
          if (pref.topics && pref.topics.length > 0) {
            setSelectedTopics(pref.topics);
          }
          if (pref.last_delivery) {
            setLastTelemetry(pref.last_delivery);
          }
        }
      } catch (err) {
        console.warn("Using default briefing preferences:", err);
      }
    }
    loadData();
  }, []);

  const handleSavePreferences = async (overrides: Partial<any> = {}) => {
    setIsSaving(true);
    try {
      const payload = {
        email,
        enabled: overrides.enabled !== undefined ? overrides.enabled : enabled,
        delivery_time: overrides.deliveryTime || deliveryTime,
        timezone,
        story_count: overrides.storyCount !== undefined ? overrides.storyCount : storyCount,
        topics: overrides.topics || selectedTopics,
      };
      await updateBriefingPreferences(payload);
      showToast("Briefing preferences saved!");
    } catch (err) {
      showToast("Failed to update preferences");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSendTest = async () => {
    setIsSendingTest(true);
    try {
      const res = await sendTestBriefing(email);
      const count = res.stories_delivered ?? storyCount;
      showToast(`Test briefing dispatched — ${count} stories sent!`);
      // Update telemetry after successful test dispatch
      setLastTelemetry((prev) => ({
        ...prev,
        status: "SENT",
        stories_count: count,
        delivered_at: new Date().toISOString(),
      }));
    } catch (err) {
      showToast("Failed to dispatch test briefing");
    } finally {
      setIsSendingTest(false);
    }
  };

  const handleSendVerification = async () => {
    setIsSendingVerification(true);
    try {
      await sendVerificationEmail(email);
      showToast("Verification email sent — check your inbox!");
    } catch (err) {
      showToast("Failed to send verification email");
    } finally {
      setIsSendingVerification(false);
    }
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const toggleTopic = (topicId: string) => {
    const updated = selectedTopics.includes(topicId)
      ? selectedTopics.filter((t) => t !== topicId)
      : [...selectedTopics, topicId];
    setSelectedTopics(updated);
    handleSavePreferences({ topics: updated });
  };

  const deliveryStatusColor =
    lastTelemetry?.status === "DELIVERED" || lastTelemetry?.status === "SENT"
      ? "text-emerald-400"
      : lastTelemetry?.status === "FAILED" || lastTelemetry?.status === "BOUNCED"
      ? "text-red-400"
      : "text-muted-foreground";

  return (
    <Container className="py-12 max-w-4xl">
      <PageHeader
        title="Settings & Preferences"
        description="Customize your AI newsroom appearance, notifications, and account details."
      />

      {/* Toast Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-primary text-primary-foreground px-4 py-3 rounded-xl shadow-lg border border-primary/20 text-sm font-mono animate-in fade-in slide-in-from-bottom-4">
          <Sparkles className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="mt-8 space-y-6">
        {/* Daily Briefing Section */}
        <div className="rounded-2xl border border-primary/30 bg-card/80 backdrop-blur-xl p-6 sm:p-8 space-y-6 shadow-md relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -z-10 pointer-events-none" />

          {/* Header & Toggle */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5 text-primary">
                <Mail className="w-5 h-5" />
                <h3 className="font-bold text-xl text-foreground font-sans tracking-tight">Daily Briefing</h3>
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                Get the most important technology stories delivered to your inbox every morning.
              </p>
            </div>

            {/* Toggle — disabled until verified */}
            <button
              onClick={() => {
                if (!emailVerified) {
                  showToast("Verify your email to enable Daily Briefing.");
                  return;
                }
                const nextVal = !enabled;
                setEnabled(nextVal);
                handleSavePreferences({ enabled: nextVal });
              }}
              className={`flex items-center gap-2.5 px-4 py-2 rounded-full font-mono text-xs font-semibold tracking-wider transition-all ${
                enabled
                  ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              } ${!emailVerified ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <span>{enabled ? "ON" : "OFF"}</span>
              <span className={`w-2 h-2 rounded-full ${enabled ? "bg-white animate-pulse" : "bg-muted-foreground"}`} />
            </button>
          </div>

          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Delivery Time & Recipient Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Delivery Time */}
              <div className="space-y-2">
                <label htmlFor="delivery-time-select" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Delivery Time</label>
                <div className="flex items-center gap-2 bg-background/60 border border-white/10 rounded-xl px-3.5 py-2.5">
                  <Clock className="w-4 h-4 text-muted-foreground" />
                  <select
                    id="delivery-time-select"
                    value={deliveryTime}
                    onChange={(e) => {
                      setDeliveryTime(e.target.value);
                      handleSavePreferences({ deliveryTime: e.target.value });
                    }}
                    className="bg-transparent text-sm font-mono text-foreground focus:outline-none w-full cursor-pointer"
                  >
                    <option value="07:00">Every day at 7:00 AM</option>
                    <option value="08:00">Every day at 8:00 AM</option>
                    <option value="09:00">Every day at 9:00 AM</option>
                    <option value="18:00">Every evening at 6:00 PM</option>
                  </select>
                </div>
              </div>

              {/* Recipient Email */}
              <div className="space-y-2">
                <label htmlFor="recipient-email-input" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Recipient Email</label>
                <div className="flex items-center gap-2 bg-background/60 border border-white/10 rounded-xl px-3.5 py-2.5">
                  <input
                    id="recipient-email-input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onBlur={() => handleSavePreferences()}
                    className="bg-transparent text-sm font-mono text-foreground focus:outline-none w-full"
                  />
                  {emailVerified ? (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md shrink-0">
                      <CheckCircle2 className="w-3 h-3" /> Verified
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md shrink-0">
                      <AlertCircle className="w-3 h-3" /> Unverified
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Verification notice — shown only when unverified */}
            {!emailVerified && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                <div className="flex items-start gap-2.5">
                  <MailCheck className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-mono text-amber-300 font-semibold">Email verification required</p>
                    <p className="text-[11px] font-mono text-amber-400/70 mt-0.5">
                      A verification link will be sent to confirm this address before briefings are activated.
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleSendVerification}
                  disabled={isSendingVerification}
                  className="flex items-center gap-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 px-4 py-2 rounded-lg text-xs font-mono font-semibold transition-all shrink-0 disabled:opacity-50"
                >
                  {isSendingVerification ? "Sending..." : "Verify Email"}
                </button>
              </div>
            )}

            {/* Action Buttons Row */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-white/5">
              <button
                onClick={handleSendTest}
                disabled={isSendingTest || !emailVerified}
                title={!emailVerified ? "Verify your email first" : undefined}
                className="flex items-center justify-center gap-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 px-5 py-2.5 rounded-xl text-xs font-mono font-semibold transition-all w-full sm:w-auto disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSendingTest ? "Sending..." : "Send test briefing"}</span>
              </button>

              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
              >
                <span>Advanced preferences</span>
                {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* Advanced Preferences Accordion */}
            {showAdvanced && (
              <div className="pt-4 border-t border-white/10 space-y-5 animate-in fade-in duration-200">
                {/* Story Count — stronger selected contrast */}
                <div className="space-y-2">
                  <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider block">Stories Delivered</span>
                  <div className="flex gap-3">
                    {[5, 10].map((count) => (
                      <button
                        key={count}
                        onClick={() => {
                          setStoryCount(count);
                          handleSavePreferences({ storyCount: count });
                        }}
                        className={`flex-1 py-2.5 rounded-xl border text-xs font-mono transition-all ${
                          storyCount === count
                            ? "border-foreground/60 bg-foreground/10 text-foreground font-bold ring-1 ring-foreground/20 shadow-sm"
                            : "border-white/10 bg-background/40 text-muted-foreground hover:border-white/25 hover:text-foreground/70"
                        }`}
                      >
                        Top {count} Stories
                      </button>
                    ))}
                  </div>
                </div>

                {/* Topics Selection */}
                <div className="space-y-2">
                  <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider block">Preferred Topics</span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                    {AVAILABLE_TOPICS.map((topic) => {
                      const isChecked = selectedTopics.includes(topic.id);
                      return (
                        <button
                          key={topic.id}
                          onClick={() => toggleTopic(topic.id)}
                          className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-left text-xs font-mono transition-all ${
                            isChecked
                              ? "border-primary/50 bg-primary/10 text-primary"
                              : "border-white/10 bg-background/40 text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            readOnly
                            className="rounded border-white/20 bg-background text-primary focus:ring-0"
                          />
                          <span className="truncate">{topic.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Telemetry Footer — split Last Briefing vs Current Preference */}
            <div className="rounded-xl bg-background/40 border border-white/5 overflow-hidden">
              <div className="grid grid-cols-2 divide-x divide-white/5">
                {/* Last Briefing */}
                <div className="px-4 py-3 space-y-1">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Last Briefing</p>
                  {lastTelemetry ? (
                    <>
                      <p className="text-[11px] font-mono text-foreground/80">
                        {formatDeliveryTime(lastTelemetry.delivered_at)}
                        {" · "}
                        {lastTelemetry.stories_count ?? "—"} stories
                      </p>
                      <span className={`text-[10px] font-mono font-semibold ${deliveryStatusColor}`}>
                        {lastTelemetry.status ?? "—"}
                      </span>
                    </>
                  ) : (
                    <p className="text-[11px] font-mono text-muted-foreground">No deliveries yet</p>
                  )}
                </div>

                {/* Current Preference */}
                <div className="px-4 py-3 space-y-1">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Current Preference</p>
                  <p className="text-[11px] font-mono text-foreground/80">
                    Top {storyCount} Stories
                  </p>
                  <p className="text-[10px] font-mono text-muted-foreground">
                    {deliveryTime} · {timezone}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Appearance & Theme Section */}
        <div className="rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-6 sm:p-8 space-y-4 shadow-sm">
          <div className="flex items-center gap-2.5 text-primary">
            <Eye className="w-5 h-5" />
            <h3 className="font-semibold text-lg text-foreground font-sans">Appearance & Theme</h3>
          </div>
          <p className="text-xs text-muted-foreground font-mono">
            Switch between Light, Dark, or System mode for a tailored editorial reading experience.
          </p>
          <div className="pt-2">
            <ThemeToggle variant="settings" />
          </div>
        </div>

        {/* Profile Information Section */}
        <div className="rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-6 sm:p-8 space-y-3 shadow-sm">
          <div className="flex items-center gap-2.5 text-primary">
            <User className="w-5 h-5" />
            <h3 className="font-semibold text-lg text-foreground font-sans">Profile & Personalization</h3>
          </div>
          <p className="text-xs text-muted-foreground font-mono">
            Your reading history, topic bookmarks, and AI preferences are automatically synced safely across your devices.
          </p>
        </div>

        {/* Data & Privacy Section */}
        <div className="rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-6 sm:p-8 space-y-3 shadow-sm">
          <div className="flex items-center gap-2.5 text-primary">
            <Shield className="w-5 h-5" />
            <h3 className="font-semibold text-lg text-foreground font-sans">Data & Privacy</h3>
          </div>
          <p className="text-xs text-muted-foreground font-mono">
            You maintain complete sovereignty over your newsroom data.
          </p>
          <div className="flex gap-4 pt-2">
            <button className="text-xs font-mono text-primary hover:underline font-medium uppercase tracking-wider">Export My Data</button>
            <button className="text-xs font-mono text-destructive hover:underline font-medium uppercase tracking-wider">Clear Browsing History</button>
          </div>
        </div>
      </div>
    </Container>
  );
}
