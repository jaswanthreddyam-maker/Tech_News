// design-system/accessibility/reducedMotion.ts
import { useReducedMotion } from "framer-motion";

export function useAppReducedMotion() {
  return useReducedMotion() ?? false;
}

export function getReducedVariants(variants: any, shouldReduceMotion: boolean) {
  if (!shouldReduceMotion) return variants;
  
  // A helper to strip heavy motion like translating or scaling, 
  // keeping only opacity fades for users preferring reduced motion.
  const reduced = { ...variants };
  for (const key in reduced) {
    if (reduced[key]) {
      const { opacity, transition } = reduced[key];
      reduced[key] = {
        opacity: opacity !== undefined ? opacity : 1,
        transition: transition ? { ...transition, duration: 0.15, ease: "linear" } : { duration: 0.15, ease: "linear" }
      };
    }
  }
  return reduced;
}
