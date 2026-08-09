'use client';

import React, { useState, useEffect } from 'react';

export default function ThreeDCardSandbox() {
  const [rotation, setRotation] = useState({ x: 0, y: 30 }); // Hardcoded to 30deg Y initially

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 60; // -30 to 30 deg
      const y = (e.clientY / window.innerHeight - 0.5) * -60; // -30 to 30 deg
      setRotation({ x: y, y: x });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);
  

  const thickness = 16;
  const cardWidth = 320;
  const cardHeight = 440;

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center overflow-hidden text-white" style={{ perspective: '1800px' }}>
      <h1 className="absolute top-10 text-2xl font-bold text-zinc-400">Pure CSS 3D Geometry Sandbox</h1>
      <p className="absolute top-20 text-zinc-500">RotateY: {rotation.y.toFixed(1)}° | RotateX: {rotation.x.toFixed(1)}°</p>

      <div 
        className="relative"
        style={{
          width: cardWidth,
          height: cardHeight,
          transformStyle: 'preserve-3d',
          transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
          // Smooth out the mouse movement slightly without Framer Motion
          transition: 'transform 0.1s linear'
        }}
      >
        {/* Extruded Object Wrapper */}
        <div 
          className="absolute inset-0 w-full h-full"
          style={{ transformStyle: 'preserve-3d' }}
        >
          {/* Back Face (Push back by thickness) */}
          <div 
            className="absolute inset-0 bg-[#0c0d0f] rounded-xl border border-white/5"
            style={{ transform: `translateZ(-${thickness}px)` }}
          />
          
          {/* Top Face (Rotate up and back) */}
          <div 
            className="absolute left-4 right-4 top-0 bg-[#3a3b3e]" 
            style={{ 
              height: thickness, 
              transformOrigin: 'top', 
              transform: 'rotateX(-90deg)' 
            }} 
          />
          
          {/* Bottom Face (Rotate down and back) */}
          <div 
            className="absolute left-4 right-4 bottom-0 bg-[#2a2b2e]" 
            style={{ 
              height: thickness, 
              transformOrigin: 'bottom', 
              transform: 'rotateX(90deg)' 
            }} 
          />
          
          {/* Left Face (Rotate left and back) */}
          <div 
            className="absolute top-4 bottom-4 left-0 bg-[#ff0055]" // NEON PINK to unequivocally prove visibility
            style={{ 
              width: thickness, 
              transformOrigin: 'left', 
              transform: 'rotateY(90deg)' 
            }} 
          />
          
          {/* Right Face (Rotate right and back) */}
          <div 
            className="absolute top-4 bottom-4 right-0 bg-[#00ffaa]" // NEON GREEN to unequivocally prove visibility
            style={{ 
              width: thickness, 
              transformOrigin: 'right', 
              transform: 'rotateY(-90deg)' 
            }} 
          />

          {/* Front Face */}
          <div 
            className="absolute inset-0 bg-[#1a1b1e] rounded-xl p-6 flex flex-col justify-end border border-white/10"
            style={{ 
              transform: 'translateZ(0px)',
              transformStyle: 'preserve-3d'
            }}
          >
            <div className="bg-zinc-800/50 w-full h-32 mb-4 rounded-lg" style={{ transform: 'translateZ(10px)' }}></div>
            <h2 className="text-xl font-bold" style={{ transform: 'translateZ(15px)' }}>Front Face</h2>
            <p className="text-zinc-400 text-sm mt-2" style={{ transform: 'translateZ(5px)' }}>If you can read this and see the NEON walls, the extrusion works flawlessly.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
