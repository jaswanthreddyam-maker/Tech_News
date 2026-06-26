import * as React from "react";
import { Sparkles } from "lucide-react";
import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <Link href="/" className="flex items-center justify-center space-x-2 mb-8">
          <Sparkles className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg tracking-tight">Tech News Today</span>
        </Link>
        {children}
      </div>
    </div>
  );
}
