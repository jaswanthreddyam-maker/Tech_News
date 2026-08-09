import React from "react";
import { Mail, MessageSquare, Globe } from "lucide-react";

export const metadata = {
  title: "Contact Us | Tech News Today",
  description: "Get in touch with the Tech News Today engineering and editorial team.",
};

export default function ContactPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-foreground space-y-12">
      <div className="space-y-4 border-b border-border/40 pb-8">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Contact Us
        </h1>
        <p className="text-lg text-muted-foreground">
          Have feedback, technical questions, or newsroom inquiries? We would love to hear from you.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="p-8 rounded-2xl border border-border/50 bg-card/50 space-y-4">
          <Mail className="w-8 h-8 text-primary" />
          <h3 className="text-xl font-bold">Engineering & API Inquiries</h3>
          <p className="text-sm text-muted-foreground">
            For API access, developer partnerships, or system integrations:
          </p>
          <p className="font-mono text-sm text-primary">support@technewstoday.com</p>
        </div>

        <div className="p-8 rounded-2xl border border-border/50 bg-card/50 space-y-4">
          <MessageSquare className="w-8 h-8 text-indigo-400" />
          <h3 className="text-xl font-bold">Editorial & Corrections</h3>
          <p className="text-sm text-muted-foreground">
            To report story corrections, request source attribution, or submit press releases:
          </p>
          <p className="font-mono text-sm text-indigo-400">editorial@technewstoday.com</p>
        </div>
      </div>
    </div>
  );
}
