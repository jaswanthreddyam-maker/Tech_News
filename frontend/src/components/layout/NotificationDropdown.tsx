"use client";

import * as React from "react";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNotifications, NotificationItem } from "@/components/providers/NotificationProvider";
import { useAppStore } from "@/store/useStore";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { EmptyState, EmptyIllustration } from "@/components/common/EmptyState";

export function NotificationDropdown() {
  const { user } = useAppStore();
  const { notifications, unreadCount, markAsRead, markAllAsRead, isConnected } = useNotifications();
  const [open, setOpen] = React.useState(false);

  if (!user) return null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative h-8 w-8 rounded-full">
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-red-500 text-[8px] text-white">
              <span className="sr-only">New notifications</span>
            </span>
          )}
          <span className="sr-only">Notifications</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-sm">Notifications</h4>
            {isConnected ? (
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" title="Connected to real-time stream" />
            ) : (
              <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" title="Connecting..." />
            )}
          </div>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={markAllAsRead} className="h-auto px-2 py-1 text-xs">
              Mark all as read
            </Button>
          )}
        </div>
        <ScrollArea className="h-80">
          {notifications.length === 0 ? (
            <div className="h-64 flex flex-col justify-center">
              <EmptyState size="sm">
                <EmptyIllustration
                  icon={Bell}
                  title="Caught up"
                  description="You have no new notifications."
                />
              </EmptyState>
            </div>
          ) : (
            <div className="flex flex-col">
              {notifications.map((notification) => (
                <NotificationCard 
                  key={notification.id} 
                  notification={notification} 
                  onRead={() => markAsRead(notification.id)}
                  onClose={() => setOpen(false)}
                />
              ))}
            </div>
          )}
        </ScrollArea>
        <div className="border-t p-2">
          <Button variant="ghost" size="sm" className="w-full text-xs" asChild onClick={() => setOpen(false)}>
            <Link href="/dashboard">View all in Dashboard</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function NotificationCard({ notification, onRead, onClose }: { notification: NotificationItem, onRead: () => void, onClose: () => void }) {
  const isUnread = !notification.readAt;

  const content = (
    <div 
      className={cn(
        "flex flex-col gap-1 border-b px-4 py-3 text-sm transition-colors hover:bg-muted/50",
        isUnread && "bg-muted/30"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className={cn("font-medium line-clamp-1", isUnread ? "text-foreground" : "text-muted-foreground")}>
          {notification.title}
        </span>
        {isUnread && <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />}
      </div>
      <p className="line-clamp-2 text-xs text-muted-foreground">
        {notification.message}
      </p>
      <span className="text-[10px] text-muted-foreground/80">
        {new Date(notification.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  );

  if (notification.url) {
    return (
      <Link 
        href={notification.url} 
        onClick={() => { 
          if (isUnread) onRead(); 
          onClose(); 
        }} 
        className="block"
      >
        {content}
      </Link>
    );
  }

  return (
    <button 
      className="w-full text-left block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring" 
      onClick={() => { 
        if (isUnread) onRead(); 
      }}
    >
      {content}
    </button>
  );
}
