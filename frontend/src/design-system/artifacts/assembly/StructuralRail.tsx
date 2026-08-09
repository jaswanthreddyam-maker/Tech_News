import React from 'react';

/**
 * StructuralRail - Ultralight Background Aluminum Track
 * 
 * Sits quietly behind the slot grid as a subtle structural mounting axis:
 * - 1px hairline brushed track
 * - Reduced opacity (`opacity-10`) so artifacts remain the hero
 */
export function StructuralRail() {
  return (
    <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-[1px] pointer-events-none z-0 px-8">
      <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  );
}
