"use client";

import { useEffect, useRef } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    // Focus the heading on mount to alert screen readers
    headingRef.current?.focus();

    // Cannot reliably use context providers here because global-error catches root layout errors
    if (typeof window !== "undefined" && window.workbox === undefined) {
       // Minimal telemetry ping if possible, ignoring complex dependencies
       fetch("/api/v1/telemetry/errors", {
         method: "POST",
         headers: { "Content-Type": "application/json" },
         body: JSON.stringify({ level: "fatal", message: error.message, stack: error.stack })
       }).catch(() => {});
    }
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div 
          role="alert"
          style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif', padding: '1rem', textAlign: 'center' }}
        >
          <div style={{ maxWidth: '500px' }}>
            <h1 
              ref={headingRef}
              tabIndex={-1}
              style={{ fontSize: '2rem', marginBottom: '1rem', color: '#ef4444', outline: 'none' }}
            >
              Critical Application Error
            </h1>
            <p style={{ color: '#6b7280', marginBottom: '2rem', lineHeight: 1.5 }}>
              We experienced a severe error that prevented the application from loading. 
              Please try again or return to the homepage.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button 
                onClick={() => reset()}
                style={{ padding: '0.75rem 1.5rem', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Try again
              </button>
              <button 
                onClick={() => window.location.href = '/'}
                style={{ padding: '0.75rem 1.5rem', background: 'transparent', color: '#374151', border: '1px solid #d1d5db', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Go home
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
