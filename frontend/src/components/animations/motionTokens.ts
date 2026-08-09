/**
 * Centralized Motion Tokens enforcing consistent motion grammar across the application.
 */
export const MOTION_TOKENS = {
  // Durations
  DURATION_STANDARD: 0.8, // 800ms
  DURATION_FAST: 0.25,     // 250ms
  DURATION_REVEAL: 0.75,   // 750ms

  // Staggers
  STAGGER_SMALL: 0.08,     // 80ms
  STAGGER_MEDIUM: 0.15,    // 150ms

  // Offsets & Blurs
  REVEAL_OFFSET_Y: 24,     // 24px
  REVEAL_BLUR: 8,          // 8px

  // Curves & Easings
  EASING_REVEAL: [0.22, 1, 0.36, 1] as const, // cubic-bezier(.22, 1, .36, 1)
  EASING_IDLE: "easeInOut" as const,

  // Springs
  SPRING_FOCUS: { stiffness: 120, damping: 28, mass: 0.8 },
  SPRING_CAMERA_LIGHT: { stiffness: 40, damping: 30, mass: 1.5 },

  // Idle Motion Durations (seconds)
  IDLE_BREATHING_DESK: 12,
  IDLE_BREATHING_WALL: 16,
  IDLE_BREATHING_FLOATING: 19,
  IDLE_CAMERA_DRIFT: 28,
};
