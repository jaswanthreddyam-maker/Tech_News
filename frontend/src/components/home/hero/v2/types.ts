import { FeaturedArticle } from "../types";

export type InteractionMode = "idle" | "hover" | "drag" | "keyboard" | "reading";
export type PlaybackState = "playing" | "paused" | "transitioning";

export interface HeroSceneState {
  items: FeaturedArticle[];
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
  activeIndex: number;
  activeArticle: FeaturedArticle | null;
  rotation: number;
  interactionMode: InteractionMode;
  playbackState: PlaybackState;
  focusedCardId: string | null;
  arrivalFinished: boolean;
}

export interface HeroSceneActions {
  setActiveIndex: (index: number | ((prev: number) => number)) => void;
  nextSlide: () => void;
  prevSlide: () => void;
  setInteractionMode: (mode: InteractionMode) => void;
  setPlaybackState: (state: PlaybackState) => void;
  setFocusedCardId: (id: string | null) => void;
  setRotation: (rotation: number | ((prev: number) => number)) => void;
  setArrivalFinished: (finished: boolean) => void;
}

export interface HeroSceneContextType extends HeroSceneState, HeroSceneActions {
  itemCount: number;
  radius: number;
  anglePerItem: number;
  onPrimaryAction?: (article: FeaturedArticle) => void;
  onInsightClick?: (article: FeaturedArticle) => void;
}

export interface HeroSceneProps {
  items: FeaturedArticle[];
  editorPicks: FeaturedArticle[];
  latest: FeaturedArticle[];
  aiInsights: FeaturedArticle[];
  initialIndex?: number;
  onSlideChange?: (index: number) => void;
  onPrimaryAction?: (article: FeaturedArticle) => void;
  onInsightClick?: (article: FeaturedArticle) => void;
}
