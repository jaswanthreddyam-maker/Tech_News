// design-system/motion/tokens.ts
import { Transition } from "framer-motion";

export const MotionTokens: Record<string, Transition> = {
  hover: {
    type: "spring",
    stiffness: 420,
    damping: 30,
    mass: 0.8,
  },
  reveal: {
    type: "spring",
    stiffness: 120,
    damping: 22,
    mass: 1,
  },
  modal: {
    type: "spring",
    stiffness: 300,
    damping: 28,
    mass: 0.9,
  },
};

export const MotionScales = {
  hover: 1.02,
  card: 1.015,
  tap: 0.98,
};
