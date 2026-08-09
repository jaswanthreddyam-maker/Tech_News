export const TRENDING_LAYOUT = {
  MAX_WIDTH: 1400,
  FEATURE_COLS: 5,
  COMPACT_COLS: 7,
  THUMBNAIL_SIZE: 80,
  MAX_COMPACT: 9,
} as const;

export const CAMERA_CONFIG = {
  DEADZONE: 0.05,
  MAX_TILT_DEG: 3.5, // Refined 3.5° ambient 3D section tilt
  LERP_FACTOR: 0.06, // Ultra-smooth 60fps rAF lerp inertia
} as const;

const HERO_BASE_DEPTH = 20;
const TILE_BASE_DEPTH = 18;

export const PHYSICAL_DEPTH = {
  hero: {
    image: HERO_BASE_DEPTH,
    title: HERO_BASE_DEPTH - 4,
    badge: HERO_BASE_DEPTH - 8,
    metadata: HERO_BASE_DEPTH - 6,
    summary: HERO_BASE_DEPTH - 10,
  },
  tile: {
    thumbnail: TILE_BASE_DEPTH,
    title: TILE_BASE_DEPTH - 4,
    badge: TILE_BASE_DEPTH - 8,
    metadata: TILE_BASE_DEPTH - 6,
  },
} as const;

export const DEFAULT_FALLBACK_IMAGES = [] as const;
