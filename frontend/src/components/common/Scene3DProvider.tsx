"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useMotionValue, useSpring, useTransform, useReducedMotion } from 'framer-motion';

interface Scene3DContextType {
  hoveredCardId: string | null;
  setHoveredCardId: (id: string | null) => void;
  rotateX: import('framer-motion').MotionValue<number>;
  rotateY: import('framer-motion').MotionValue<number>;
}

const Scene3DContext = createContext<Scene3DContextType | undefined>(undefined);

export function useScene3D() {
  const ctx = useContext(Scene3DContext);
  if (!ctx) throw new Error("useScene3D must be used within a Scene3DProvider");
  return ctx;
}

interface Scene3DProviderProps {
  children: React.ReactNode;
  className?: string;
  cameraMaxRotateX?: number; // e.g., 3
  cameraMaxRotateY?: number; // e.g., 5
}

export function Scene3DProvider({ 
  children, 
  className = "",
  cameraMaxRotateX = 3,
  cameraMaxRotateY = 5
}: Scene3DProviderProps) {
  const [hoveredCardId, setHoveredCardId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  // Mouse tracking (-1 to 1)
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Springs for camera (stiffness 120, damping 28, mass 0.8)
  const springConfig = { stiffness: 120, damping: 28, mass: 0.8 };
  const cameraX = useSpring(mouseX, springConfig);
  const cameraY = useSpring(mouseY, springConfig);

  // Springs for light (lagging behind camera)
  const lightSpringConfig = { stiffness: 40, damping: 30, mass: 1.5 }; // Slower, heavier
  const lightX = useSpring(mouseX, lightSpringConfig);
  const lightY = useSpring(mouseY, lightSpringConfig);

  // Transforms to actual CSS rotation angles
  const rotateX = useTransform(cameraY, [-1, 1], [cameraMaxRotateX, -cameraMaxRotateX]);
  const rotateY = useTransform(cameraX, [-1, 1], [-cameraMaxRotateY, cameraMaxRotateY]);

  // Use a rAF loop to write the motion values to CSS variables for peak performance
  useEffect(() => {
    if (shouldReduceMotion) return;

    let rafId: number;
    const updateCSSVariables = () => {
      if (containerRef.current) {
        // Camera Rotations
        containerRef.current.style.setProperty('--camera-rotate-x', `${rotateX.get()}deg`);
        containerRef.current.style.setProperty('--camera-rotate-y', `${rotateY.get()}deg`);
        // Normalized Camera Position (for parallax calculations)
        containerRef.current.style.setProperty('--camera-norm-x', `${cameraX.get()}`);
        containerRef.current.style.setProperty('--camera-norm-y', `${cameraY.get()}`);
        // Light Positions (-1 to 1 mapped to percentages for radial gradients)
        const lx = (lightX.get() + 1) * 50; // 0 to 100%
        const ly = (lightY.get() + 1) * 50; // 0 to 100%
        containerRef.current.style.setProperty('--light-x', `${lx}%`);
        containerRef.current.style.setProperty('--light-y', `${ly}%`);
      }
      rafId = requestAnimationFrame(updateCSSVariables);
    };
    rafId = requestAnimationFrame(updateCSSVariables);
    return () => cancelAnimationFrame(rafId);
  }, [rotateX, rotateY, cameraX, cameraY, lightX, lightY, shouldReduceMotion]);

  useEffect(() => {
    if (shouldReduceMotion) return;

    const handleMouseMove = (e: MouseEvent) => {
      const normX = (e.clientX / window.innerWidth) * 2 - 1;
      const normY = (e.clientY / window.innerHeight) * 2 - 1;
      mouseX.set(normX);
      mouseY.set(normY);
    };

    const handleMouseLeave = () => {
      mouseX.set(0);
      mouseY.set(0);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [mouseX, mouseY, shouldReduceMotion]);

  return (
    <Scene3DContext.Provider value={{ hoveredCardId, setHoveredCardId, rotateX, rotateY }}>
      <div ref={containerRef} className={`relative w-full ${className}`}>
        {children}
      </div>
    </Scene3DContext.Provider>
  );
}
