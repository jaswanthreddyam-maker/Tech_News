"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAppStore } from "../../store/useStore";
import { canAccessAdmin, hasPermission, PERMISSIONS } from "@/lib/auth/permissions";
import { apiFetch } from "../../services/api";
import { getNotifications, Notification } from "../../services/api/admin";
import {
  LayoutDashboard,
  Radio,
  FileText,
  TrendingUp,
  Cpu,
  CircleDollarSign,
  Activity,
  Users,
  ScrollText,
  ToggleLeft,
  ShieldAlert,
  LogOut,
  Menu,
  X,
  Bell,
  ChevronRight,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  permission?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "DASHBOARD",
    items: [
      { label: "Overview", href: "/admin", icon: LayoutDashboard },
    ],
  },
  {
    title: "NEWS OPERATIONS",
    items: [
      { label: "Sources", href: "/admin/sources", icon: Radio, permission: PERMISSIONS.MANAGE_SOURCES },
      { label: "Articles", href: "/admin/articles", icon: FileText, permission: PERMISSIONS.REVIEW_ARTICLES },
      { label: "Trends", href: "/admin/trends", icon: TrendingUp, permission: PERMISSIONS.MANAGE_TRENDS },
    ],
  },
  {
    title: "AI OPERATIONS",
    items: [
      { label: "AI Queue", href: "/admin/ai", icon: Cpu, permission: PERMISSIONS.MANAGE_AI_QUEUE },
      { label: "Costs", href: "/admin/ai?tab=costs", icon: CircleDollarSign, permission: PERMISSIONS.MANAGE_AI_QUEUE },
    ],
  },
  {
    title: "INFRASTRUCTURE",
    items: [
      { label: "Telemetry", href: "/admin/telemetry", icon: Activity, permission: PERMISSIONS.VIEW_TELEMETRY },
    ],
  },
  {
    title: "MANAGEMENT",
    items: [
      { label: "Users", href: "/admin/users", icon: Users, permission: PERMISSIONS.MANAGE_USERS },
      { label: "Audit Logs", href: "/admin/audit", icon: ScrollText, permission: PERMISSIONS.VIEW_AUDIT_LOGS },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { label: "Feature Flags", href: "/admin/flags", icon: ToggleLeft, permission: PERMISSIONS.MANAGE_FEATURE_FLAGS },
      { label: "Emergency", href: "/admin/emergency", icon: ShieldAlert, permission: PERMISSIONS.EMERGENCY_CONTROLS },
    ],
  },
];

function getRoleBadgeColor(role: string): string {
  switch (role) {
    case "super_admin":
      return "text-red-400 border-red-400/30";
    case "admin":
      return "text-amber-400 border-amber-400/30";
    case "editor":
      return "text-emerald-400 border-emerald-400/30";
    default:
      return "text-neutral-400 border-neutral-400/30";
  }
}

function getPageTitle(pathname: string): string {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length <= 1) return "OPERATIONS OVERVIEW";
  const last = segments[segments.length - 1];
  const titles: Record<string, string> = {
    sources: "SOURCE MANAGEMENT",
    articles: "ARTICLE MODERATION",
    trends: "TREND ANALYTICS",
    ai: "AI OPERATIONS",
    telemetry: "TELEMETRY CENTER",
    users: "USER MANAGEMENT",
    audit: "AUDIT LOG",
    flags: "FEATURE FLAGS",
    emergency: "EMERGENCY OPERATIONS",
  };
  return titles[last] || last.toUpperCase();
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logoutUser, accessToken, isRestoringSession } = useAppStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Auth guard
  useEffect(() => {
    if (!mounted || isRestoringSession) return;
    if (!user || !accessToken) {
      router.push("/login");
      return;
    }
    if (!canAccessAdmin(user)) {
      router.push("/");
      return;
    }
  }, [mounted, user, accessToken, isRestoringSession, router]);

  // Fetch notifications
  useEffect(() => {
    if (!mounted || !accessToken) return;
    const fetchNotifications = async () => {
      try {
        const data = await getNotifications();
        setNotifications(data);
      } catch {
        // Notifications are non-critical
      }
    };
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [mounted, accessToken]);

  const handleLogout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // Logout endpoint may fail, but we still clear local state
    }
    logoutUser();
    router.push("/login");
  }, [logoutUser, router]);

  const markNotificationRead = async (id: number) => {
    try {
      await apiFetch(`/admin/notifications/${id}/read`, { method: "POST" });
      setNotifications((prev) => (Array.isArray(prev) ? prev : []).filter((n) => n.id !== id));
    } catch {
      // Non-critical
    }
  };

  const isActive = (href: string) => {
    if (href === "/admin") return pathname === "/admin";
    return pathname.startsWith(href.split("?")[0]);
  };

  const safeNotifications = Array.isArray(notifications) ? notifications : [];
  const unreadCount = (Array.isArray(safeNotifications) ? safeNotifications : []).filter((n) => !n.read_at).length;

  if (!mounted || !user) {
    return (
      <div className="min-h-screen bg-[#080808] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-5 h-5 border border-white/20 border-t-white animate-spin" />
          <span className="font-mono text-[9px] tracking-widest uppercase text-[#555]">
            INITIALIZING OPERATIONS CENTER
          </span>
        </div>
      </div>
    );
  }

  const filteredSections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => {
      if (!item.permission) return true;
      return hasPermission(user, item.permission);
    }),
  })).filter((section) => section.items.length > 0);

  return (
    <div className="min-h-screen bg-[#080808] flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          role="presentation"
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => { if (e.key === 'Escape') setSidebarOpen(false); }}
        />
      )}

      {/* LEFT SIDEBAR */}
      <aside
        className={`fixed lg:sticky top-0 left-0 h-screen w-56 bg-[#0a0a0a] border-r border-[#1a1a1a] flex flex-col z-50 transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Sidebar header */}
        <div className="p-4 border-b border-[#1a1a1a]">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold tracking-tight text-white font-sans uppercase">
                TECH NEWS TODAY
              </h2>
              <p className="font-mono text-[7px] tracking-[0.2em] uppercase text-[#555] mt-0.5">
                OPERATIONS CENTER
              </p>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-[#555] hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* User info */}
        <div className="px-4 py-3 border-b border-[#1a1a1a]">
          <p className="text-[11px] font-sans font-medium text-white truncate">
            {user.name}
          </p>
          <div className="mt-1 flex items-center gap-1.5">
            <span
              className={`inline-block font-mono text-[7px] tracking-widest uppercase border px-1.5 py-0.5 ${getRoleBadgeColor(
                user.role
              )}`}
            >
              {user.role.replace("_", " ")}
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-2">
          {filteredSections.map((section) => (
            <div key={section.title} className="mb-1">
              <div className="px-4 py-2">
                <span className="font-mono text-[8px] text-[#555] uppercase tracking-[0.2em]">
                  {section.title}
                </span>
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <button
                    key={item.href}
                    onClick={() => {
                      router.push(item.href.split("?")[0]);
                      setSidebarOpen(false);
                    }}
                    className={`w-full flex items-center gap-2 py-2 px-3 font-mono text-[11px] transition-colors ${
                      active
                        ? "text-white bg-[#111] border-l-2 border-white"
                        : "text-[#888] hover:text-white hover:bg-[#111] border-l-2 border-transparent"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Logout */}
        <div className="p-3 border-t border-[#1a1a1a]">
          <button
            id="admin-logout"
            onClick={handleLogout}
            className="w-full flex items-center gap-2 py-2 px-3 font-mono text-[11px] text-red-400 hover:text-red-300 hover:bg-[#111] transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* MAIN VIEWPORT */}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Top bar */}
        <header className="shrink-0 bg-[#0a0a0a] border-b border-[#1a1a1a] px-4 lg:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-[#888] hover:text-white transition-colors"
            >
              <Menu className="w-4 h-4" />
            </button>

            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase">
              <span className="text-[#555]">OPS</span>
              <ChevronRight className="w-2.5 h-2.5 text-[#333]" />
              <span className="text-white font-medium">{getPageTitle(pathname)}</span>
            </div>
          </div>

          {/* Notification bell */}
          <div className="relative">
            <button
              id="admin-notifications"
              onClick={() => setShowNotifications(!showNotifications)}
              className="relative text-[#888] hover:text-white transition-colors p-1"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[14px] h-[14px] flex items-center justify-center bg-red-500 text-white font-mono text-[7px] font-bold px-0.5">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </button>

            {/* Notifications dropdown */}
            {showNotifications && (
              <div className="absolute right-0 top-full mt-2 w-72 border border-[#1a1a1a] bg-[#0c0c0c] z-50 shadow-xl">
                <div className="px-3 py-2 border-b border-[#1a1a1a]">
                  <span className="font-mono text-[9px] tracking-widest uppercase text-[#888]">
                    NOTIFICATIONS
                  </span>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {safeNotifications.length === 0 ? (
                    <div className="px-3 py-4 text-center">
                      <p className="font-mono text-[10px] text-[#555]">No notifications</p>
                    </div>
                  ) : (
                    safeNotifications.slice(0, 10).map((n: any) => (
                      <button
                        key={n.id}
                        type="button"
                        className="w-full text-left px-3 py-2 border-b border-[#111] hover:bg-[#111] transition-colors cursor-pointer block"
                        onClick={() => markNotificationRead(n.id)}
                      >
                        <p className="font-mono text-[10px] text-white leading-relaxed">
                          {n.message || n.title}
                        </p>
                        <p className="font-mono text-[8px] text-[#555] mt-0.5" suppressHydrationWarning>
                          {n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                        </p>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto bg-[#080808] p-4 lg:p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
