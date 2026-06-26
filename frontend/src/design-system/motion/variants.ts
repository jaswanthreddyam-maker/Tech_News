// design-system/motion/variants.ts
import { Variants } from "framer-motion";
import { MotionTokens } from "./tokens";

export const fadeRevealVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: {
    opacity: 1,
    y: 0,
    transition: MotionTokens.reveal
  }
};

export const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: MotionTokens.modal
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 20,
    transition: { ...MotionTokens.modal, duration: 0.15 } // faster exit
  }
};
