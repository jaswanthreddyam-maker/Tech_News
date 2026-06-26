import { ReactNode } from "react";
import { Search, Folder, Bookmark, LayoutDashboard, Settings, LogOut, Sun, Moon, Bell } from "lucide-react";

export interface CommandDefinition {
  id: string;
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  group: string;
  keywords?: string[];
  shortcut?: string[];
  action: () => void;
  hidden?: () => boolean;
  disabled?: () => boolean;
}

// Global registry of all available commands
const commands: CommandDefinition[] = [];

export function registerCommand(command: CommandDefinition) {
  // Prevent duplicate IDs
  if (!commands.find(c => c.id === command.id)) {
    commands.push(command);
  }
}

export function getCommands(): CommandDefinition[] {
  // Filter out hidden commands at runtime
  return commands.filter(c => !(c.hidden && c.hidden()));
}

// Base commands that are always registered
export function registerBaseCommands(dependencies: { 
  router: any, 
  setTheme: (t: string) => void, 
  logout: () => void,
  isAuthenticated: boolean
}) {
  const baseCommands: CommandDefinition[] = [
    {
      id: "search",
      title: "Search Articles",
      subtitle: "Find news and trends",
      icon: <Search className="w-4 h-4" />,
      group: "Navigation",
      action: () => dependencies.router.push("/search"),
      shortcut: ["S"],
      hidden: () => true, // Temporarily disabled
    },
    {
      id: "dashboard",
      title: "Open Dashboard",
      subtitle: "View your personalized hub",
      icon: <LayoutDashboard className="w-4 h-4" />,
      group: "Navigation",
      action: () => dependencies.router.push("/dashboard"),
      hidden: () => !dependencies.isAuthenticated,
    },
    {
      id: "notifications",
      title: "Notifications",
      subtitle: "View your alerts",
      icon: <Bell className="w-4 h-4" />,
      group: "Navigation",
      action: () => dependencies.router.push("/dashboard"),
      hidden: () => !dependencies.isAuthenticated,
    },
    {
      id: "collections",
      title: "My Collections",
      icon: <Folder className="w-4 h-4" />,
      group: "Library",
      action: () => dependencies.router.push("/dashboard"),
      hidden: () => !dependencies.isAuthenticated,
    },
    {
      id: "bookmarks",
      title: "My Bookmarks",
      icon: <Bookmark className="w-4 h-4" />,
      group: "Library",
      action: () => dependencies.router.push("/dashboard"),
      hidden: () => !dependencies.isAuthenticated,
    },
    {
      id: "theme-light",
      title: "Switch to Light Theme",
      icon: <Sun className="w-4 h-4" />,
      group: "Settings",
      action: () => dependencies.setTheme("light"),
    },
    {
      id: "theme-dark",
      title: "Switch to Dark Theme",
      icon: <Moon className="w-4 h-4" />,
      group: "Settings",
      action: () => dependencies.setTheme("dark"),
    },
    {
      id: "settings",
      title: "Account Settings",
      icon: <Settings className="w-4 h-4" />,
      group: "Settings",
      action: () => dependencies.router.push("/dashboard/settings"),
      hidden: () => !dependencies.isAuthenticated,
    },
    {
      id: "logout",
      title: "Log out",
      icon: <LogOut className="w-4 h-4" />,
      group: "Settings",
      action: () => {
        dependencies.logout();
        dependencies.router.push("/");
      },
      hidden: () => !dependencies.isAuthenticated,
    }
  ];

  baseCommands.forEach(registerCommand);
}
