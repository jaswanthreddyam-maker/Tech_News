/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";
import "../styles/globals.css";
import ErrorBoundary from "../components/ui/ErrorBoundary";
import AuthProvider from "../components/AuthProvider";
import GoogleAuthWrapper from "../components/GoogleAuthWrapper";
import { NotificationProvider } from "../components/providers/NotificationProvider";
import { PersonalizationProvider } from "../components/providers/PersonalizationProvider";

import { AnalyticsProvider } from "../components/providers/AnalyticsProvider";
import { TelemetryProvider } from "../components/providers/TelemetryProvider";
import { ErrorProvider } from "../components/providers/ErrorProvider";
import { PerformanceProvider } from "../components/providers/PerformanceProvider";
import { InstallProvider } from "../components/providers/InstallProvider";
import { QueryProvider } from "../components/providers/QueryProvider";
import { Toaster } from "../components/ui/toaster";

import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { AnimationProvider } from "@/components/providers/AnimationProvider";
import { WelcomeOverlay } from "@/components/layout/WelcomeOverlay";

export const metadata: Metadata = {
  title: "Tech News Today | Autonomous AI Newsroom",
  description: "AI-powered real-time technology news portal. Discover emerging innovations in Artificial Intelligence, Robotics, and Startups.",
  keywords: ["technology news", "AI newsroom", "robotics news", "startup news", "artificial intelligence"],
  authors: [{ name: "Tech News Today Team" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body className="font-sans antialiased bg-background text-foreground min-h-screen flex flex-col">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <QueryProvider>
            <AnalyticsProvider>
              <TelemetryProvider>
                <ErrorProvider>
                  <PerformanceProvider>
                    <InstallProvider>
                      <ErrorBoundary>
                        <GoogleAuthWrapper>
                          <AuthProvider>
                            <NotificationProvider>
                              <PersonalizationProvider>
                                <AnimationProvider>
                                  <WelcomeOverlay>
                                    {children}
                                  </WelcomeOverlay>
                                  <Toaster />
                                </AnimationProvider>
                              </PersonalizationProvider>
                            </NotificationProvider>
                          </AuthProvider>
                        </GoogleAuthWrapper>
                      </ErrorBoundary>
                    </InstallProvider>
                  </PerformanceProvider>
                </ErrorProvider>
              </TelemetryProvider>
            </AnalyticsProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
