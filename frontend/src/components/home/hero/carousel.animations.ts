import { Variants } from "framer-motion";

export const getImageVariants = (reduced: boolean): Variants => ({
  initial: { scale: reduced ? 1.0 : 1.05, opacity: 0 },
  animate: { scale: 1.0, opacity: 1, transition: { duration: 0.55, ease: "easeInOut" } },
  exit: { opacity: 0, transition: { duration: 0.3 } }
});

export const getHeadlineVariants = (reduced: boolean): Variants => ({
  initial: { opacity: 0, y: reduced ? 0 : 10 },
  animate: { opacity: 1, y: 0, transition: { delay: 0.12, duration: 0.35, ease: "easeOut" } },
  exit: { opacity: 0, y: reduced ? 0 : -10, transition: { duration: 0.2 } }
});

export const getSummaryVariants = (): Variants => ({
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { delay: 0.22, duration: 0.45, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.2 } }
});

export const getPrimaryActionVariants = (): Variants => ({
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { delay: 0.32, duration: 0.45, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.2 } }
});

export const getSidebarVariants = (): Variants => ({
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { delay: 0.45, duration: 0.45, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.2 } }
});
