import React from 'react';

interface ArtifactMaterialProps {
  children: React.ReactNode;
  variant?: 'glass' | 'metal';
}

/**
 * ArtifactMaterial - CNC Product Material Layer
 * "What substance am I made of?"
 * 
 * Recreates physical smoked glass and anodized aluminum finishes:
 * - Satin top chamfer highlight (1px specular light catch)
 * - Deep body mass shading without artificial borders
 */
export function ArtifactMaterial({ children, variant = 'glass' }: ArtifactMaterialProps) {
  const isGlass = variant === 'glass';

  return (
    <div 
      className={`absolute inset-0 rounded-[13px] overflow-hidden ${isGlass ? 'bg-[#121318]' : 'bg-[#0f1014]'}`}
      style={{
        transformStyle: 'preserve-3d',
        backfaceVisibility: 'hidden',
        boxShadow: `
          inset 0 1px 0 rgba(255, 255, 255, 0.12),
          0 8px 24px rgba(0, 0, 0, 0.8),
          0 2px 6px rgba(0, 0, 0, 0.6)
        `
      }}
    >
      {/* Subtle top-to-bottom material gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/[0.03] via-transparent to-black/20 pointer-events-none" />
      {children}
    </div>
  );
}
