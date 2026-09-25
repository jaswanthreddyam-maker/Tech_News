"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  Shield, User, Mail, Send, CheckCircle2,
  ChevronDown, ChevronUp, Sparkles, Clock, AlertCircle, MailCheck,
  Bell, BellRing, LogOut, Check,
} from "lucide-react";
import {
  getBriefingPreferences,
  updateBriefingPreferences,
  sendTestBriefing,
  sendVerificationEmail,
} from "@/lib/api/briefing";
import { useAppStore } from "@/store/useStore";
import { useNotifications } from "@/components/providers/NotificationProvider";
import { useAuthGate } from "@/hooks/useAuthGate";
import { FeatureCapability } from "@/lib/auth/features";

const AVAILABLE_TOPICS = [
  { id: "artificial-intelligence", label: "AI & Neural Systems" },
  { id: "technology", label: "General Technology" },
  { id: "cybersecurity", label: "Cybersecurity" },
  { id: "hardware", label: "Hardware & Devices" },
  { id: "startups-and-business", label: "Startups & VC" },
  { id: "science", label: "Science & Quantum" },
];

const DELIVERY_TIME_OPTIONS = [
  { value: "07:00", label: "Every day at 7:00 AM", period: "Early Morning" },
  { value: "08:00", label: "Every day at 8:00 AM", period: "Morning Edition (Default)" },
  { value: "09:00", label: "Every day at 9:00 AM", period: "Mid-Morning" },
  { value: "18:00", label: "Every evening at 6:00 PM", period: "Evening Edition" },
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
  const router = useRouter();
  const { user } = useAppStore();
  const { notifications, unreadCount, markAllAsRead, isConnected } = useNotifications();
  const { requireAuthentication } = useAuthGate();
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
  const [isTimeDropdownOpen, setIsTimeDropdownOpen] = useState(false);
  const timeDropdownRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (timeDropdownRef.current && !timeDropdownRef.current.contains(event.target as Node)) {
        setIsTimeDropdownOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsTimeDropdownOpen(false);
      }
    }
    if (isTimeDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isTimeDropdownOpen]);
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
  }, [user?.email]);

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

  const selectedTimeOption =
    DELIVERY_TIME_OPTIONS.find((opt) => opt.value === deliveryTime) || {
      value: deliveryTime,
      label: `Every day at ${deliveryTime}`,
      period: "Custom Time",
    };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader
        title="Settings & Preferences"
        description="Customize your account identity, daily briefing, notifications, and data privacy."
      />

      {/* Toast Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-primary text-primary-foreground px-4 py-3 rounded-xl shadow-lg border border-primary/20 text-sm font-mono animate-in fade-in slide-in-from-bottom-4">
          <Sparkles className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="space-y-6">
        {/* Profile & Account Section */}
        <div className="rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-6 sm:p-8 space-y-5 shadow-sm">
          <div className="flex items-center justify-between gap-4 pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-full border border-primary/30 bg-primary/10 text-primary">
                <User className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg text-foreground font-sans">Profile & Account</h3>
                <p className="text-xs text-muted-foreground font-mono">
                  Your identity, authentication credentials, and synchronized session state.
                </p>
              </div>
            </div>
            {user && (
              <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" /> Authenticated
              </span>
            )}
          </div>

          {user ? (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-background/50 border border-white/5">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="h-14 w-14 rounded-full border-2 border-primary/40 bg-primary/15 text-primary flex items-center justify-center font-bold text-lg font-mono shadow-md">
                    {user.name
                      ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
                      : "JR"}
                  </div>
                  <span className="absolute bottom-0 right-0 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-background" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-base text-foreground font-sans">{user.name || "Authenticated Operator"}</h4>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-white/10 text-neutral-300">
                      {typeof user.role === "string" ? user.role : "Member"}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5" />
                    {user.email}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 pt-2 sm:pt-0">
                <button
                  onClick={() => {
                    useAppStore.getState().logoutUser();
                    window.location.href = "/login";
                  }}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-mono font-semibold text-destructive bg-destructive/10 hover:bg-destructive/20 border border-destructive/30 transition-all cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-background/50 border border-white/5">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full border border-white/10 bg-white/[0.04] flex items-center justify-center text-muted-foreground font-mono font-bold">
                  ?
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Guest Reader Mode</p>
                  <p className="text-xs text-muted-foreground font-mono">Sign in to save bookmarks, unlock AI copilot, and customize feeds.</p>
                </div>
              </div>
              <button
                onClick={() => requireAuthentication(FeatureCapability.SAVED_ARTICLES, { returnUrl: "/dashboard/settings" })}
                className="px-5 py-2.5 rounded-xl text-xs font-mono font-bold uppercase tracking-wider bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm transition-all shrink-0 cursor-pointer"
              >
                Sign In / Register
              </button>
            </div>
          )}
        </div>
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

            {/* Toggle — high-contrast cybernetic switch with non-blending colors */}
            <button
              type="button"
              role="switch"
              aria-checked={enabled}
              aria-label="Toggle Daily Briefing"
              onClick={() => {
                if (!emailVerified) {
                  showToast("Verify your email to enable Daily Briefing.");
                  return;
                }
                const nextVal = !enabled;
                setEnabled(nextVal);
                handleSavePreferences({ enabled: nextVal });
              }}
              className={`group flex items-center gap-3 px-3.5 py-1.5 rounded-full font-mono text-xs font-bold tracking-wider transition-all duration-300 border select-none ${
                enabled
                  ? "bg-emerald-500/15 border-emerald-500/60 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.25)] hover:bg-emerald-500/25 hover:border-emerald-400"
                  : "bg-neutral-900 border-neutral-700/80 text-neutral-300 hover:border-neutral-500 hover:text-white hover:bg-neutral-800/80 shadow-inner"
              } ${!emailVerified ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <span className="tracking-widest font-mono text-[11px]">
                {enabled ? "ON" : "OFF"}
              </span>

              {/* High-contrast sliding switch track */}
              <span
                className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors duration-300 ${
                  enabled ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" : "bg-neutral-700"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform duration-300 ${
                    enabled ? "translate-x-4" : "translate-x-0"
                  }`}
                />
              </span>
            </button>
          </div>

          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Delivery Time & Recipient Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Delivery Time — Custom Cybernetic Dropdown */}
              <div className="space-y-2 relative" ref={timeDropdownRef}>
                <span id="delivery-time-label" className="text-xs font-mono text-muted-foreground uppercase tracking-wider block">
                  Delivery Time
                </span>
                <button
                  type="button"
                  id="delivery-time-select"
                  aria-haspopup="listbox"
                  aria-expanded={isTimeDropdownOpen}
                  aria-labelledby="delivery-time-label"
                  onClick={() => setIsTimeDropdownOpen((prev) => !prev)}
                  className={`w-full flex items-center justify-between gap-3 bg-background/80 hover:bg-card/90 border rounded-xl px-3.5 py-2.5 transition-all text-left group cursor-pointer ${
                    isTimeDropdownOpen
                      ? "border-primary/60 ring-2 ring-primary/20 shadow-lg"
                      : "border-white/10 hover:border-white/25"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Clock className={`w-4 h-4 transition-colors shrink-0 ${isTimeDropdownOpen ? "text-primary" : "text-muted-foreground group-hover:text-primary"}`} />
                    <span className="text-sm font-mono text-foreground font-medium truncate">
                      {selectedTimeOption.label}
                    </span>
                  </div>
                  <ChevronDown
                    className={`w-4 h-4 text-muted-foreground transition-transform duration-200 shrink-0 ${
                      isTimeDropdownOpen ? "rotate-180 text-primary" : "group-hover:text-foreground"
                    }`}
                  />
                </button>

                {/* Custom Cybernetic Dropdown Menu */}
                {isTimeDropdownOpen && (
                  <div
                    role="listbox"
                    aria-labelledby="delivery-time-label"
                    className="absolute top-full left-0 right-0 mt-2 z-50 bg-[#121214] border border-white/15 rounded-xl shadow-[0_16px_36px_rgba(0,0,0,0.85)] backdrop-blur-2xl p-1.5 space-y-1 animate-in fade-in zoom-in-95 duration-150"
                  >
                    {DELIVERY_TIME_OPTIONS.map((opt) => {
                      const isSelected = opt.value === deliveryTime;
                      return (
                        <button
                          key={opt.value}
                          role="option"
                          aria-selected={isSelected}
                          type="button"
                          onClick={() => {
                            setDeliveryTime(opt.value);
                            handleSavePreferences({ deliveryTime: opt.value });
                            setIsTimeDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left text-xs font-mono transition-all cursor-pointer ${
                            isSelected
                              ? "bg-primary/15 text-primary border border-primary/30 font-semibold shadow-sm"
                              : "text-neutral-200 hover:bg-white/[0.08] hover:text-white border border-transparent"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <Clock className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-primary" : "text-muted-foreground"}`} />
                            <div className="flex flex-col min-w-0">
                              <span className={`truncate ${isSelected ? "text-primary font-semibold" : "text-foreground"}`}>
                                {opt.label}
                              </span>
                              <span className="text-[10px] text-muted-foreground">
                                {opt.period}
                              </span>
                            </div>
                          </div>
                          {isSelected && (
                            <Check className="w-4 h-4 text-primary shrink-0 ml-2" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
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


        {/* In-App Notifications & Alerts Section */}
        <div className="rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-6 sm:p-8 space-y-5 shadow-sm">
          <div className="flex items-center justify-between gap-4 pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-full border border-primary/30 bg-primary/10 text-primary">
                <Bell className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg text-foreground font-sans">In-App Notifications & Alerts</h3>
                <p className="text-xs text-muted-foreground font-mono">
                  Real-time breaking tech event stream and editorial publication updates.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isConnected ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live Stream Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <span className="w-2 h-2 rounded-full bg-amber-400" /> Standby
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-background/50 border border-white/5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <BellRing className="w-4 h-4 text-primary" />
                  <span>Unread Notifications</span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-primary/20 text-primary border border-primary/30">
                  {unreadCount} Unread
                </span>
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                {notifications.length} total alerts recorded in current session.
              </p>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="mt-2 text-xs font-mono text-primary hover:underline font-medium uppercase tracking-wider"
                >
                  Mark all as read
                </button>
              )}
            </div>

            <div className="p-4 rounded-xl bg-background/50 border border-white/5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground">Header Quick Access</span>
                <span className="text-xs font-mono text-emerald-400 font-semibold">Active</span>
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                The notification bell and profile badge in the top navigation bar provide instant drop-down access across all pages.
              </p>
            </div>
          </div>
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
    </div>
  );
}
