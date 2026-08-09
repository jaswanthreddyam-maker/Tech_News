import React from 'react';

interface ArtifactLightingProps {
  children: React.ReactNode;
  cardIndex?: number;
}

/**
 * ArtifactLighting
 * "How do I react to light?"
 * 
 * Responsible strictly for:
 * - Dynamic glare planes & micro-spatial reflection variances
 * - Environmental reflections
 * - Subsurface scattering effects
 */
export function ArtifactLighting({ children, cardIndex = 0 }: ArtifactLightingProps) {
  // Spatial light sheen offsets per card index to eliminate cloned lighting
  const lightPositions = [
    '30% 20%', // Feature: top-left accent
    '65% 25%', // Compact 1: top-right sheen
    '20% 35%', // Compact 2: left sheen
    '80% 40%', // Compact 3: far right sheen
    '40% 70%', // Compact 4: lower center sheen
    '75% 65%', // Compact 5: lower right sheen
    '35% 50%', // Compact 6: center left sheen
  ];

  const pos = lightPositions[cardIndex % lightPositions.length];

  return (
    <>
      {/* Ambient Micro-Spatial Specular Light Sheen */}
      <div 
        className="absolute inset-0 pointer-events-none z-40 rounded-[14px]"
        style={{
          background: `radial-gradient(ellipse at ${pos}, rgba(255, 255, 255, 0.08) 0%, transparent 65%)`,
          transform: 'translateZ(1px)'
        }}
      />

      {/* Dynamic Glare Plane (Active on mouse move) */}
      <div 
        className="absolute inset-0 pointer-events-none mix-blend-overlay z-50 rounded-[14px]"
        style={{
          background: 'radial-gradient(circle at var(--light-x, 50%) var(--light-y, 50%), rgba(255, 255, 255, calc(0.25 * var(--light-intensity, 0))), transparent 60%)',
          transform: 'translateZ(2px)',
          transformStyle: 'preserve-3d'
        }}
      />
      {children}
    </>
  );
}
