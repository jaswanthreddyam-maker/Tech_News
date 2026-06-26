"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useToast } from "@/hooks/use-toast";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { BUILD_CONFIG } from "@/config/build";
import { useTelemetry } from "./TelemetryProvider";

declare global {
  interface Window {
    workbox: any;
  }
}

interface InstallContextType {
  isInstallable: boolean;
  installPrompt: any;
  promptInstall: () => void;
}

const InstallContext = createContext<InstallContextType | undefined>(undefined);

export function InstallProvider({ children }: { children: React.ReactNode }) {
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const { toast } = useToast();
  const { logPerformance } = useTelemetry();

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e);
      logPerformance("PWA Installable", 1);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
  }, [logPerformance]);

  // Handle service worker versioning and updates
  useEffect(() => {
    if (typeof window !== "undefined" && "serviceWorker" in navigator && window.workbox !== undefined) {
      const wb = window.workbox;

      wb.addEventListener("waiting", () => {
        toast({
          title: "Update available",
          description: "A new version of Tech News Today is available.",
          action: (
            <button
              onClick={() => {
                wb.addEventListener("controlling", () => {
                  window.location.reload();
                });
                wb.messageSkipWaiting();
              }}
              className="bg-primary text-primary-foreground px-3 py-1 rounded text-sm"
            >
              Reload
            </button>
          ),
          duration: Number.POSITIVE_INFINITY,
        });
      });

      wb.register();
    }
  }, [toast]);

  const promptInstall = async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === "accepted") {
      setInstallPrompt(null);
      logPerformance("PWA Installed", 1);
    }
  };

  return (
    <InstallContext.Provider value={{ isInstallable: !!installPrompt, installPrompt, promptInstall }}>
      {children}
    </InstallContext.Provider>
  );
}

export function useInstall() {
  const context = useContext(InstallContext);
  if (context === undefined) {
    throw new Error("useInstall must be used within an InstallProvider");
  }
  return context;
}
