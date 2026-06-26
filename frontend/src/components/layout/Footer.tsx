import * as React from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";

const footerLinks = {
  Product: [
    { label: "Home", href: "/" },
    // { label: "Search", href: "/search" },
    { label: "Topics", href: "/topics" },
  ],
  Company: [
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
    { label: "Privacy", href: "/privacy" },
  ],
  Developers: [
    { label: "API Docs", href: "/docs" },
    { label: "Design System", href: "/design-system" },
    { label: "Status", href: "/status" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-screen-2xl px-4 md:px-6 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center space-x-2 mb-4">
              <Sparkles className="h-5 w-5 text-primary" />
              <span className="font-bold text-sm tracking-tight">Tech News Today</span>
            </Link>
            <p className="text-sm text-muted-foreground max-w-xs">
              AI-powered autonomous newsroom delivering real-time technology intelligence.
            </p>
          </div>

          {/* Link Columns */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-sm font-semibold mb-3">{category}</h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-hover"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="mt-12 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Tech News Today. Built with AI.
          </p>
          <p className="text-xs text-muted-foreground font-mono">
            v1.0.0-rc1
          </p>
        </div>
      </div>
    </footer>
  );
}
