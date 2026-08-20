import * as React from "react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Equal, Moon, Eye, Mail, Send, CheckCircle2, Sparkles, ExternalLink } from "lucide-react";
import { getBriefingPreferences, updateBriefingPreferences, sendTestBriefing } from "@/lib/api/briefing";

interface SettingsDialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export function SettingsDialog({ open, onOpenChange, trigger }: SettingsDialogProps) {
  const [enabled, setEnabled] = React.useState(false);
  const [email, setEmail] = React.useState("jeshu@example.com");
  const [isSendingTest, setIsSendingTest] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [statusMsg, setStatusMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      getBriefingPreferences(email)
        .then((pref) => {
          if (pref) {
            setEnabled(pref.enabled);
            if (pref.email) setEmail(pref.email);
          }
        })
        .catch(() => {});
    }
  }, [open, email]);

  const showStatus = (msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(null), 4000);
  };

  const handleToggleSync = async () => {
    const nextVal = !enabled;
    setEnabled(nextVal);
    setIsSaving(true);
    try {
      await updateBriefingPreferences({
        email,
        enabled: nextVal,
        delivery_time: "08:00",
        timezone: "Asia/Kolkata",
        story_count: 5,
        topics: ["artificial-intelligence", "technology"],
      });
      showStatus(nextVal ? "Email Briefing Sync Enabled!" : "Email Briefing Sync Disabled.");
    } catch {
      showStatus("Failed to update briefing sync");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSendTest = async () => {
    setIsSendingTest(true);
    try {
      const res = await sendTestBriefing(email);
      showStatus(`Test briefing sent to ${email} (${res.stories_delivered || 5} stories)!`);
    } catch {
      showStatus("Failed to send test briefing");
    } finally {
      setIsSendingTest(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="sm:max-w-[480px] bg-background/95 backdrop-blur-2xl border border-white/15 text-foreground shadow-2xl rounded-2xl p-6">
        <DialogHeader className="space-y-1 pb-3 border-b border-white/10">
          <div className="flex items-center gap-2 text-primary font-mono text-xs uppercase tracking-widest font-semibold">
            <Equal className="w-4 h-4" strokeWidth={2} />
            <span>Preferences & Email Sync</span>
          </div>
          <DialogTitle className="text-xl font-bold font-sans">Settings</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground font-mono">
            Customize your AI newsroom appearance and daily email briefing sync.
          </DialogDescription>
        </DialogHeader>

        {statusMsg && (
          <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-primary text-xs font-mono flex items-center gap-2">
            <Sparkles className="w-4 h-4 shrink-0" />
            <span>{statusMsg}</span>
          </div>
        )}

        <div className="py-2 space-y-5">
          {/* Daily Briefing Email Sync */}
          <div className="space-y-3 p-4 rounded-xl border border-white/15 bg-white/[0.03]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-foreground">
                <Mail className="w-4 h-4 text-primary" />
                <span className="text-xs font-bold font-sans">Daily Email Briefing Sync</span>
              </div>
              <button
                onClick={handleToggleSync}
                disabled={isSaving}
                className={`px-3 py-1 rounded-full font-mono text-[11px] font-semibold tracking-wider transition-all ${
                  enabled
                    ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {enabled ? "ENABLED" : "DISABLED"}
              </button>
            </div>

            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Get curated tech stories delivered directly to your email every morning.
            </p>

            <div className="space-y-2 pt-1">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                className="w-full px-3 py-2 text-xs font-mono bg-background border border-white/10 rounded-lg focus:outline-none focus:border-primary text-foreground"
              />
              <button
                type="button"
                onClick={handleSendTest}
                disabled={isSendingTest || !email}
                className="w-full py-2 bg-muted/60 hover:bg-muted text-foreground border border-white/10 rounded-lg text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5 text-primary" />
                <span>{isSendingTest ? "Sending Test Briefing..." : "Send Test Briefing Now"}</span>
              </button>
            </div>
          </div>

          {/* Appearance & Theme Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3.5 rounded-xl border border-white/15 bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-primary">
                  <Moon className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold font-sans">Dark Theme (Locked)</div>
                  <div className="text-[10px] text-muted-foreground font-mono">Pitch OLED dark aesthetic</div>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                Active
              </span>
            </div>
          </div>

          {/* Full Settings Page Link */}
          <div className="pt-1">
            <Link
              href="/settings"
              onClick={() => onOpenChange?.(false)}
              className="w-full py-2.5 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-mono font-semibold flex items-center justify-center gap-2 shadow-sm transition-all"
            >
              <span>Open Full Settings & Preferences</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
