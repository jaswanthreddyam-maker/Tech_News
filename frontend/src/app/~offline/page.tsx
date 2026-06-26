"use client";

import { OfflineState } from "@/components/common/ErrorState";

export default function OfflinePage() {
  return (
    <div className="flex h-screen items-center justify-center p-4">
      <OfflineState 
        onRetry={() => {
          if (typeof window !== "undefined") window.location.reload();
        }} 
      />
    </div>
  );
}
