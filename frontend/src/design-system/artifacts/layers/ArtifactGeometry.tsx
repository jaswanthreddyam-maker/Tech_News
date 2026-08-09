import React from 'react';

interface ArtifactGeometryProps {
  children: React.ReactNode;
  thickness?: number;
  proudZ?: number;
  className?: string;
  isHovered?: boolean;
}

/**
 * ArtifactGeometry
 * "What shape am I?"
 * 
 * Responsible strictly for physical presence:
 * - Extrusion walls (thickness)
 * - Bevels / edges
 * - Grounding shadow receiver
 * - Hover elevation mechanics
 */
export function ArtifactGeometry({ 
  children, 
  thickness = 20, 
  proudZ = 2,
  className = '',
  isHovered = false
}: ArtifactGeometryProps) {
  
  // Preloaded proud seating offset (2-4px) + Z-travel on hover
  const translateZ = proudZ + (isHovered ? 16 : 0);
  
  return (
    <div 
      className={`relative w-full h-full ${className}`}
      style={{ 
        transformStyle: 'preserve-3d',
        transform: `translateZ(${translateZ}px)`,
        transition: 'transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1)'
      }}
    >
      {/* Back Face (Grounds the shadow, establishes proud cavity separation) */}
      <div 
        className="absolute inset-0 rounded-[13px] bg-[#07080b]"
        style={{
          transformStyle: 'preserve-3d',
          backfaceVisibility: 'hidden',
          transform: `translateZ(-${thickness}px)`,
          boxShadow: 'inset 0 0 0 1px rgba(0, 0, 0, 0.95), 0 20px 48px rgba(0,0,0,0.9), 0 6px 16px rgba(0,0,0,0.75)'
        }}
      />

      {/* Extrusion Geometry (Side Walls) */}
      <div 
        className="absolute top-4 bottom-4 left-0 origin-left"
        style={{
          width: thickness,
          transformStyle: 'preserve-3d',
          backfaceVisibility: 'hidden',
          transform: 'rotateY(90deg)',
          background: 'linear-gradient(to right, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.05) 1px, #141518 2px, #060608 100%)'
        }}
      />
      <div 
        className="absolute top-4 bottom-4 right-0 origin-right"
        style={{
          width: thickness,
          transformStyle: 'preserve-3d',
          backfaceVisibility: 'hidden',
          transform: 'rotateY(-90deg)',
          background: 'linear-gradient(to left, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.05) 1px, #141518 2px, #060608 100%)'
        }}
      />
      <div 
        className="absolute left-4 right-4 top-0 origin-top"
        style={{
          height: thickness,
          transformStyle: 'preserve-3d',
          backfaceVisibility: 'hidden',
          transform: 'rotateX(-90deg)',
          background: 'linear-gradient(to bottom, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0.08) 1px, #1c1d22 2px, #060608 100%)'
        }}
      />
      <div 
        className="absolute left-4 right-4 bottom-0 origin-bottom"
        style={{
          height: thickness,
          transformStyle: 'preserve-3d',
          backfaceVisibility: 'hidden',
          transform: 'rotateX(90deg)',
          background: 'linear-gradient(to top, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.02) 1px, #08090a 2px, #020202 100%)'
        }}
      />

      {/* Mounting Plate (Front Face Base) */}
      <div 
        className="relative w-full h-full rounded-[13px]"
        style={{
          transformStyle: 'preserve-3d',
          transform: 'translateZ(0px)',
        }}
      >
        {children}
      </div>
    </div>
  );
}
