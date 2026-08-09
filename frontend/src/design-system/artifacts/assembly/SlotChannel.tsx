import React from 'react';

interface SlotChannelProps {
  className?: string;
  variant?: 'feature' | 'compact';
  children?: React.ReactNode;
}

/**
 * SlotChannel — Subconscious Background Layer
 * 
 * The slot should disappear. Articles are the product.
 * Slot communicates depth through a subtle inset shadow only.
 * No visible architecture. No rails. No borders.
 */
export function SlotChannel({ className = '', variant = 'compact', children }: SlotChannelProps) {
  const isFeature = variant === 'feature';

  return (
    <div 
      className={`relative w-full rounded-[16px] ${isFeature ? 'h-full min-h-[480px]' : 'h-[140px]'} ${className}`}
      style={{
        // Subconscious depth: barely-visible inset shadow behind the artifact
        background: '#060709',
        boxShadow: 'inset 0 4px 16px rgba(0, 0, 0, 0.95)'
      }}
    >
      {/* Artifact fills the slot with a 3px tolerance reveal */}
      <div className="relative z-10 w-full h-full p-[3px] overflow-visible" style={{ transformStyle: 'preserve-3d' }}>
        {children}
      </div>
    </div>
  );
}
