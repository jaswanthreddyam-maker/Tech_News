"use client";

import * as React from "react";
import Link from "next/link";
import { useAppStore } from "@/store/useStore";
import { apiFetch } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SettingsDialog } from "@/components/layout/SettingsDialog";
import { LogOut, Shield, User as UserIcon, Mail } from "lucide-react";
import { Sliders2Icon } from "@/components/common/icons/Sliders2Icon";

export function UserMenu() {
  const { user, logoutUser } = useAppStore();
  const [settingsOpen, setSettingsOpen] = React.useState(false);

  const handleLogout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // Ignore network errors on logout
    }
    logoutUser();
    window.location.href = "/login";
  };

  if (!user) {
    return (
      <div className="flex items-center gap-1.5">
        <SettingsDialog
          trigger={
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-full border border-white/10 bg-white/[0.04] text-foreground hover:border-white/25 hover:bg-white/[0.08] transition-all"
              aria-label="Preferences"
            >
              <Sliders2Icon className="h-4 w-4 text-foreground" strokeWidth={2.2} />
            </Button>
          }
        />
        <Link href="/login">
          <Button
            size="sm"
            className="h-8 px-3.5 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 font-mono text-xs font-semibold shadow-sm transition-all"
          >
            Sign In
          </Button>
        </Link>
      </div>
    );
  }

  const initials = user.name
    ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "U";

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button id="user-menu-trigger" data-testid="user-menu-trigger" variant="ghost" size="icon" className="h-9 w-9 rounded-full border border-white/10 bg-white/[0.04] hover:border-white/25 transition-all" aria-label="User menu">
            <Avatar className="h-7 w-7">
              <AvatarFallback className="text-xs bg-primary/10 text-primary font-semibold">
                {initials}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48 bg-background/90 backdrop-blur-xl border border-white/15 text-foreground shadow-2xl rounded-xl">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">{user.name}</p>
              <p className="text-xs text-muted-foreground leading-none">{user.email}</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild className="gap-2 cursor-pointer rounded-lg hover:bg-white/10">
            <Link href="/settings">
              <Mail className="h-4 w-4 text-primary" />
              <span>Email Sync & Briefing</span>
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setSettingsOpen(true)} className="gap-2 cursor-pointer rounded-lg hover:bg-white/10">
            <Sliders2Icon className="h-4 w-4" strokeWidth={2.2} />
            Preferences
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout} className="gap-2 text-destructive focus:text-destructive cursor-pointer rounded-lg hover:bg-destructive/10">
            <LogOut className="h-4 w-4" />
            Sign Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
