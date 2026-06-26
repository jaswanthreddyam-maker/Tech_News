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
import { canAccessAdmin } from "@/lib/auth/permissions";
import { LogOut, Settings, Shield, User as UserIcon } from "lucide-react";

export function UserMenu() {
  const { user, logoutUser } = useAppStore();

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
      <Link href="/login">
        <Button variant="ghost" size="sm" className="h-8 text-xs">
          Sign In
        </Button>
      </Link>
    );
  }

  const initials = user.name
    ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "U";

  const isAdmin = canAccessAdmin(user);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button id="user-menu-trigger" data-testid="user-menu-trigger" variant="ghost" size="icon" className="h-8 w-8 rounded-full" aria-label="User menu">
          <Avatar className="h-7 w-7">
            <AvatarFallback className="text-xs bg-primary/10 text-primary font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{user.name}</p>
            <p className="text-xs text-muted-foreground leading-none">{user.email}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {isAdmin && (
          <DropdownMenuItem asChild>
            <Link href="/admin" className="gap-2 cursor-pointer">
              <Shield className="h-4 w-4" />
              Admin Dashboard
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuItem asChild>
          <Link href="/settings" className="gap-2 cursor-pointer">
            <Settings className="h-4 w-4" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="gap-2 text-destructive focus:text-destructive cursor-pointer">
          <LogOut className="h-4 w-4" />
          Sign Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
