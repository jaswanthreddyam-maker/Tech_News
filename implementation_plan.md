# Premium 3D Hero Carousel Overhaul

Transform the current "2D carousel with perspective" into a cinematic, immersive 3D rotating cylinder experience.

## User Review Required

> [!IMPORTANT]
> This is a large overhaul touching 6 files. The plan addresses all 14 critique points grouped into 5 workstreams. Changes are purely visual/interaction — no API changes, no new dependencies.

> [!WARNING]
> The blurred dynamic background (critique #4) uses the focused card's `thumbnail_url` as a full-bleed background image. If any articles have missing thumbnails, it falls back to a dark radial gradient. This means a brief image load flash on first render — mitigated with a CSS `opacity` transition.

## Open Questions

> [!IMPORTANT]
> **Card count**: Currently fetching 10 articles for the ring. With the new wider cylinder (5–7 visible), 10 works well (5 visible front + 5 hidden rear, selling the infinite illusion). Should I keep 10, or increase to 12–14 for a denser ring?

## Proposed Changes

### Workstream 1 — Geometry & Visibility (Critiques #1, #2, #3, #6, #14)

The core geometry problems: centre card too dominant, side cards cropped, weak perspective, missing rear cards, doesn't feel infinite.

---

#### [MODIFY] [carousel.constants.ts](file:///d:/tech_news/frontend/src/components/home/hero/carousel.constants.ts)

- Increase `RING_VISIBILITY_CUTOFF` from `2` → `3` (5→7 cards visible: focused + 3 each side)
- Add new constants for the expanded geometry:
  - `CARD_WIDTH = 260` (down from 290 — smaller centre card, ~55% of stage)
  - `CARD_HEIGHT = 340` (down from 350)
  - `MIN_GAP = 20` (down from 35 — tighter packing reveals more cards)
  - `PERSPECTIVE_DEPTH = 1800` (up from 1200 — wider field of view)
  - `STAGE_HEIGHT = 520` (up from 400 — more vertical breathing room, critique #9)

---

#### [MODIFY] [Hero3DRing.tsx](file:///d:/tech_news/frontend/src/components/home/hero/Hero3DRing.tsx)

**Perspective & Stage:**
- Change `perspective` from `1200px` → use `PERSPECTIVE_DEPTH` constant (`1800px`)
- Change container height from `400px` → `STAGE_HEIGHT` (`520px`)
- Move perspective origin slightly above center: `perspectiveOrigin: "50% 42%"` (tilts the cylinder slightly for a more dramatic view)
- Remove the heavy side gradient overlays (the `from-background` divs at L190–191) — they clip side cards. Replace with a very subtle vignette via `box-shadow: inset`.

**Track dimensions:**
- Track `width`/`height` → use constants from `carousel.constants.ts`

**Radius:**
- Move `CARD_WIDTH` and `MIN_GAP` into constants file
- The `computeRingRadius` function already scales dynamically — with reduced `MIN_GAP=20` and `CARD_WIDTH=260`, radius will increase naturally for 10 cards, spreading cards wider

---

#### [MODIFY] [Hero3DCard.tsx](file:///d:/tech_news/frontend/src/components/home/hero/Hero3DCard.tsx)

**Tier system expansion** (was: focused/near/far/hidden → now: focused/near/mid/far/hidden):

| Tier | Distance | Scale | Opacity | Blur | Description |
|------|----------|-------|---------|------|-------------|
| `focused` | 0 | 1.0 | 1.0 | 0px | Brightest, sharpest |
| `near` | 1 | 0.88 | 0.75 | 0.5px | Slight recession |
| `mid` | 2 | 0.78 | 0.5 | 1px | Clearly behind |
| `far` | 3 | 0.68 | 0.35 | 1.5px | Barely glimpsed |
| `hidden` | >3 | 0.6 | 0 | 2px | Behind the cylinder |

- Card dimensions: `260×340` (from constants)
- Margin offsets: `-130px` left, `-170px` top (half of new dimensions)

---

### Workstream 2 — Dynamic Background & Environmental Lighting (Critiques #4, #8, #12)

Create an immersive environment that responds to the focused article.

---

#### [MODIFY] [HeroCarouselClient.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroCarouselClient.tsx)

**Dynamic blurred background:**
- Behind the ring, render a full-bleed `<div>` containing an `<img>` of the focused article's thumbnail
- Apply: `filter: blur(50px) brightness(0.3) saturate(1.4)`, `transform: scale(1.15)` (slight zoom prevents blur edge artifacts), `object-fit: cover`
- Cross-fade between images using two stacked layers with alternating `opacity` transitions (`transition: opacity 1.2s ease`)
- Dark overlay on top: `bg-gradient-to-b from-black/60 via-black/40 to-black/70`
- Subtle vignette: `box-shadow: inset 0 0 200px 60px rgba(0,0,0,0.8)`

**Ambient spotlight / environmental glow:**
- Add a subtle radial gradient "spotlight" above the centre card: `radial-gradient(ellipse at 50% 35%, rgba(255,255,255,0.04) 0%, transparent 70%)`
- Below the ring, add a floor glow: a small `radial-gradient(ellipse at 50% 100%, rgba(var(--primary-rgb), 0.08) 0%, transparent 60%)` div

**Floor reflection:**
- Below the ring container, add a `div` with `transform: scaleY(-0.25) rotateX(2deg)`, `opacity: 0.12`, `filter: blur(4px)`, `mask-image: linear-gradient(to bottom, rgba(0,0,0,0.4), transparent)`
- This is purely decorative — it mirrors the ring track's position

---

### Workstream 3 — Card Content & Hierarchy (Critiques #5, #13)

Sharpen the visual hierarchy and trim excess text.

---

#### [MODIFY] [Hero3DCard.tsx](file:///d:/tech_news/frontend/src/components/home/hero/Hero3DCard.tsx)

**Focused card:**
- Keep: image + source badge + date + title (2-line clamp) + **1-line** summary (down from 2) + CTA
- Add subtle elevated glow: `box-shadow: 0 0 60px rgba(255,255,255,0.08), 0 20px 40px rgba(0,0,0,0.5)`
- Sharper rendering: no blur filter

**Near cards (distance 1):**
- Show: image + source badge + title (2-line)
- Apply `filter: blur(0.5px)`, reduced brightness via overlay
- Darker border: `border-white/10`

**Mid cards (distance 2):**
- Show: image + title (1-line)
- Apply `filter: blur(1px)`
- Even darker

**Far cards (distance 3):**
- Show: image only (title hidden for extreme distance)
- Apply `filter: blur(1.5px)`
- Barely visible at 35% opacity

---

### Workstream 4 — Controls & Layout (Critiques #9, #10)

Hero height and arrow placement.

---

#### [MODIFY] [HeroControls.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroControls.tsx)

- Move arrows inward — they should sit ~10% from the ring edge, not at the container edge
- Change `px-4` → `px-[12%]` (or similar responsive value) so they sit just outside the visible carousel arc
- Make them slightly larger: `p-2.5` → `p-3`, icon `w-5 h-5` → `w-6 h-6`
- Semi-transparent glass style: `bg-white/10 backdrop-blur-md border-white/20`

#### [MODIFY] [HeroCarouselClient.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroCarouselClient.tsx)

- Remove the `border border-border rounded-xl bg-card/45` on the outer container — the dynamic background provides the visual boundary now
- Add `overflow: hidden` and `rounded-2xl` for clean edge containment
- The `pt-8 pb-5` stays, but overall hero section gets more vertical space via `STAGE_HEIGHT=520`

#### [MODIFY] [page.tsx](file:///d:/tech_news/frontend/src/app/(public)/page.tsx)

- Change the Container wrapping the hero from `size="wide"` to full-bleed (no Container, or a custom `max-w-[1600px]` wrapper) so the background extends edge-to-edge
- Keep `mt-8 md:mt-10` for navbar clearance

---

### Workstream 5 — Motion & Inertia (Critique #11)

Cinematic motion with momentum.

---

#### [MODIFY] [Hero3DRing.tsx](file:///d:/tech_news/frontend/src/components/home/hero/Hero3DRing.tsx)

**Drag with inertia:**
- On pointer up, calculate velocity from drag distance / time
- If velocity exceeds threshold, advance 1–2 cards in the drag direction with momentum easing
- Use `cubic-bezier(0.25, 1, 0.5, 1)` for the deceleration curve (slightly different from snap transitions)

**Wheel with momentum:**
- Already has wheel accumulator — refine the threshold and add a smoother debounce (100ms → 80ms)

**Transition easing:**
- Keep using `EASING.standard` and `DURATION.slow` from tokens — these are already smooth
- Add a slight overshoot for snap transitions: `cubic-bezier(0.22, 1.2, 0.36, 1)` (subtle spring feel)

---

### Workstream 6 — Skeleton Update

---

#### [MODIFY] [HeroCarouselSkeleton.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroCarouselSkeleton.tsx)

- Update to match new `STAGE_HEIGHT` (520px)
- Show 3 skeleton cards in a perspective-like arrangement to preview the 3D layout

---

## Summary of All File Changes

| File | Critiques Addressed |
|------|-------------------|
| [carousel.constants.ts](file:///d:/tech_news/frontend/src/components/home/hero/carousel.constants.ts) | #1, #2, #3, #6, #9, #14 |
| [Hero3DRing.tsx](file:///d:/tech_news/frontend/src/components/home/hero/Hero3DRing.tsx) | #2, #3, #6, #8, #11, #14 |
| [Hero3DCard.tsx](file:///d:/tech_news/frontend/src/components/home/hero/Hero3DCard.tsx) | #1, #5, #7, #13 |
| [HeroCarouselClient.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroCarouselClient.tsx) | #4, #7, #8, #9, #12 |
| [HeroControls.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroControls.tsx) | #10 |
| [page.tsx](file:///d:/tech_news/frontend/src/app/(public)/page.tsx) | #9 |
| [HeroCarouselSkeleton.tsx](file:///d:/tech_news/frontend/src/components/home/hero/HeroCarouselSkeleton.tsx) | — (alignment) |

## Verification Plan

### Automated Tests
```bash
npx tsc --noEmit        # Zero type errors
npm run build           # Clean production build, check bundle size delta
```

### Manual Verification
- Hard-refresh `localhost:3000` and visually confirm:
  - 5–7 cards visible around the cylinder
  - Blurred dynamic background cross-fading on rotation
  - Subtle floor reflection and ambient glow
  - Arrows positioned just outside the carousel arc
  - Smooth inertia on drag release
  - No clipping at top/bottom of hero section
  - Rear cards glimpsed at low opacity behind the cylinder edges
