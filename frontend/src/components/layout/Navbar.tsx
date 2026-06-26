"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { UserMenu } from "@/components/layout/UserMenu";
import { NotificationDropdown } from "@/components/layout/NotificationDropdown";
import { GlobalSearchOverlay } from "@/components/search/GlobalSearchOverlay";
import {
  Search,
  Menu,
  X,
  Sparkles,
} from "lucide-react";

const navLinks = [
  { href: "/", label: "Home" },
  // { href: "/search", label: "Search" },
  { href: "/topics", label: "Topics" },
  // { href: "/workspaces", label: "Workspaces" },
];

export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);

  // Close mobile menu on route change
  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Keyboard shortcut for search (Cmd/Ctrl+K)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <nav className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-screen-2xl items-center px-4 md:px-6">
          {/* Logo */}
          <Link href="/" className="mr-6 flex items-center space-x-2 shrink-0">
            <Sparkles className="h-5 w-5 text-primary" />
            <div className="flex flex-col leading-none">
              <span className="font-bold text-sm tracking-tight">Tech News Today</span>
              <span className="text-[9px] text-muted-foreground font-mono tracking-widest uppercase">
                AI Newsroom
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-1 flex-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-button transition-colors duration-hover",
                  pathname === link.href
                    ? "text-foreground bg-secondary"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2 ml-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSearchOpen(true)}
              className="hidden lg:inline-flex items-center gap-2 text-muted-foreground text-xs h-8 px-3 w-52 justify-start"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Search...</span>
            </Button>

            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-8 w-8"
              onClick={() => setSearchOpen(true)}
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </Button>

            <NotificationDropdown />
            <ThemeToggle />
            <UserMenu />

            {/* Mobile Menu Toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-8 w-8"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            >
              {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-border bg-background/95 backdrop-blur-lg">
            <div className="flex flex-col space-y-1 px-4 py-3">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "px-3 py-2 text-sm font-medium rounded-button transition-colors",
                    pathname === link.href
                      ? "text-foreground bg-secondary"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Search Overlay */}
      <GlobalSearchOverlay open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  );
}
