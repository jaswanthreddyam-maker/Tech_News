import React from "react";
import Link from "next/link";
import { 
  LayoutDashboard, 
  Activity, 
  Target, 
  Briefcase, 
  Archive, 
  Zap, 
  ShieldCheck, 
  Settings, 
  PlaySquare, 
  BarChart, 
  FlaskConical 
} from "lucide-react";

const navGroups = [
  {
    title: "Overview",
    items: [
      { name: "Overview", href: "/ops", icon: LayoutDashboard }
    ]
  },
  {
    title: "Execution",
    items: [
      { name: "Operations", href: "/ops/operations", icon: Activity },
      { name: "Goals", href: "/ops/goals", icon: Target },
      { name: "Workspace", href: "/ops/workspace", icon: Briefcase },
      { name: "Replay", href: "/ops/replay", icon: PlaySquare },
    ]
  },
  {
    title: "Knowledge",
    items: [
      { name: "Artifacts", href: "/ops/artifacts", icon: Archive },
      { name: "Capabilities", href: "/ops/capabilities", icon: Zap },
    ]
  },
  {
    title: "Governance",
    items: [
      { name: "Policies", href: "/ops/policies", icon: ShieldCheck },
      { name: "Configuration", href: "/ops/configuration", icon: Settings },
      { name: "Evaluation", href: "/ops/evaluation", icon: FlaskConical },
    ]
  },
  {
    title: "Observability",
    items: [
      { name: "Monitoring", href: "/ops/monitoring", icon: BarChart },
    ]
  }
];

export default function OpsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-lg font-bold text-blue-400">AIOS Console</h1>
          <p className="text-xs text-slate-400">Enterprise Gateway</p>
        </div>
        <nav className="flex-1 overflow-y-auto p-4 space-y-6">
          {navGroups.map((group) => (
            <div key={group.title}>
              {group.title !== "Overview" && (
                <h3 className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  {group.title}
                </h3>
              )}
              <ul className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <li key={item.name}>
                      <Link 
                        href={item.href}
                        className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                      >
                        <Icon className="w-4 h-4" />
                        {item.name}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 border-b border-slate-800 bg-slate-900/50 flex items-center px-6">
          <h2 className="text-sm font-medium text-slate-300">Admin Mode Active</h2>
        </header>
        <div className="flex-1 overflow-auto p-6 bg-slate-950">
          {children}
        </div>
      </main>
    </div>
  );
}
