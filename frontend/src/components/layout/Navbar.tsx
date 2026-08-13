"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { NotificationDropdown } from "@/components/layout/NotificationDropdown";
import { SettingsDialog } from "@/components/layout/SettingsDialog";
import { UserMenu } from "@/components/layout/UserMenu";
import { GlobalSearchOverlay } from "@/components/search/GlobalSearchOverlay";
import { Search, Menu, X, Settings } from "lucide-react";

const navLinks: { href: string; label: string }[] = [];

/**
 * Navbar — Floating AI Newsroom Cockpit (Zero-G Magnetic Capsule)
 * 
 * 1. Solid Central Anchor: Always stays anchored at screen center (no ping-ponging or jumps).
 * 2. Magnetic Cursor Drift: Drifts max 10-12px towards cursor like a zero-gravity module in liquid space, spring-returning to center on leave.
 * 3. Organic Zero-G Breathing: 14s subtle idle float (`_nav-capsule-breathe`) keeps the interface feeling alive.
 * 4. Arc Glass Search & Theme Controls: Glassy pill search (`⌘K`) and circular theme button.
 * 5. Scroll-Driven Glass Transition: At >20px scroll, smoothly transitions to `backdrop-blur-[30px] bg-background/50 border-b border-white/[0.08]`.
 */
export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [scrolled, setScrolled] = React.useState(false);
  const [navVisible, setNavVisible] = React.useState<boolean>(() => pathname !== "/");
  const navCapsuleRef = React.useRef<HTMLDivElement>(null);

  // Listen for hero arrival completion to reveal navbar on homepage
  React.useEffect(() => {
    if (pathname !== "/") {
      setNavVisible(true);
      return;
    }

    setNavVisible(false);

    const handleArrivalComplete = () => {
      setNavVisible(true);
    };

    window.addEventListener("hero-arrival-complete", handleArrivalComplete);

    // Fallback timer (7.5s) to guarantee navbar appearance after welcome + arrival sequence
    const fallbackTimer = setTimeout(() => {
      setNavVisible(true);
    }, 7500);

    return () => {
      window.removeEventListener("hero-arrival-complete", handleArrivalComplete);
      clearTimeout(fallbackTimer);
    };
  }, [pathname]);

  // Hysteresis scroll detection to prevent mobile elastic overscroll strobing
  React.useEffect(() => {
    let isScrolled = false;
    const handleScroll = () => {
      const y = window.scrollY;
      if (!isScrolled && y > 40) {
        isScrolled = true;
        setScrolled(true);
      } else if (isScrolled && y < 15) {
        isScrolled = false;
        setScrolled(false);
      }
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Magnetic Cursor Drift Effect (Max 10-12px drift with smooth rAF inertia)
  React.useEffect(() => {
    const capsule = navCapsuleRef.current;
    if (!capsule) return;

    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let rafId: number;

    const handleMouseMove = (e: MouseEvent) => {
      const nav = capsule.closest("nav");
      if (!nav) return;
      const rect = nav.getBoundingClientRect();
      if (e.clientY < rect.top - 30 || e.clientY > rect.bottom + 30) {
        targetX = 0;
        targetY = 0;
        return;
      }

      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const offsetX = (e.clientX - centerX) / (rect.width / 2 || 1);
      const offsetY = (e.clientY - centerY) / (rect.height / 2 || 1);

      targetX = Math.max(-12, Math.min(12, offsetX * 12));
      targetY = Math.max(-4, Math.min(4, offsetY * 4));
    };

    const handleMouseLeave = () => {
      targetX = 0;
      targetY = 0;
    };

    const updateDrift = () => {
      currentX += (targetX - currentX) * 0.08;
      currentY += (targetY - currentY) * 0.08;

      if (capsule) {
        capsule.style.transform = `translate3d(${currentX.toFixed(2)}px, ${currentY.toFixed(2)}px, 0px)`;
      }
      rafId = requestAnimationFrame(updateDrift);
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("mouseleave", handleMouseLeave, { passive: true });
    rafId = requestAnimationFrame(updateDrift);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(rafId);
    };
  }, []);

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
      <nav
        className={cn(
          "sticky top-0 z-50 w-full transition-all duration-700 ease-out select-none",
          navVisible
            ? "opacity-100 translate-y-0 pointer-events-auto"
            : "opacity-0 -translate-y-4 pointer-events-none",
          scrolled
            ? "h-14 sm:h-16 bg-background/50 backdrop-blur-[30px] border-b border-white/[0.08] shadow-[0_16px_40px_-15px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.12)]"
            : "h-14 sm:h-16 bg-transparent border-b border-transparent"
        )}
      >
        {/* Subtle Ambient Hero Light Reflection Line */}
        <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none" />

        <div className="relative mx-auto flex h-full max-w-screen-2xl items-center justify-between px-4 sm:px-6 lg:px-8">
          
          {/* Left: Brand Title */}
          <Link href="/" className="group flex items-center shrink-0 z-10">
            <span className="font-extrabold text-lg sm:text-xl tracking-tight text-foreground group-hover:text-primary transition-colors">
              Tech News Today
            </span>
          </Link>

          {/* Center: Zero-G Magnetic Floating Navigation Capsule (Only rendered when links exist) */}
          {navLinks.length > 0 && (
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 hidden md:flex items-center justify-center pointer-events-auto z-10 [animation:_nav-capsule-breathe_14s_ease-in-out_infinite]">
              <div
                ref={navCapsuleRef}
                className="flex items-center p-1 rounded-full bg-white/[0.04] border border-white/[0.08] backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.12),0_8px_24px_-6px_rgba(0,0,0,0.4)] will-change-transform"
              >
                {navLinks.map((link) => {
                  const isActive = pathname === link.href;
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={cn(
                        "px-5 py-1.5 text-xs font-semibold rounded-full transition-all duration-300 relative",
                        isActive
                          ? "text-foreground bg-white/10 border border-white/20 shadow-[0_2px_10px_rgba(255,255,255,0.12),inset_0_1px_0_rgba(255,255,255,0.3)]"
                          : "text-muted-foreground hover:text-foreground hover:bg-white/[0.06]"
                      )}
                    >
                      {link.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* Right: Glass Search Capsule, Theme Toggle & Sign In */}
          <div className="flex items-center gap-2.5">
            
            {/* Arc-Style Glass Search Capsule */}
            <button
              onClick={() => setSearchOpen(true)}
              className="hidden lg:flex items-center gap-2.5 h-9 px-3.5 w-52 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/20 backdrop-blur-xl text-xs text-muted-foreground hover:text-foreground transition-all duration-300 shadow-sm group"
            >
              <Search className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
              <span>Search articles...</span>
            </button>

            {/* Mobile Search Icon Button */}
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-9 w-9 rounded-full border border-white/10 bg-white/[0.04]"
              onClick={() => setSearchOpen(true)}
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </Button>

            <NotificationDropdown />
            <UserMenu />

            {/* Mobile Menu Toggle */}
            {navLinks.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden h-9 w-9 rounded-full border border-white/10 bg-white/[0.04]"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              >
                {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </Button>
            )}
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && navLinks.length > 0 && (
          <div className="md:hidden border-b border-white/10 bg-background/90 backdrop-blur-2xl px-4 py-3 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="flex flex-col space-y-1.5 p-1 rounded-2xl bg-white/[0.04] border border-white/10">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "px-4 py-2.5 text-sm font-semibold rounded-xl transition-all",
                    pathname === link.href
                      ? "text-foreground bg-white/10 border border-white/20"
                      : "text-muted-foreground hover:text-foreground hover:bg-white/[0.06]"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* Global Search Overlay */}
      <GlobalSearchOverlay open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  );
}
