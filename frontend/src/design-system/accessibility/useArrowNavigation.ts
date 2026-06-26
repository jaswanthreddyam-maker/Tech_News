import { useCallback, useRef } from "react";

type Orientation = "horizontal" | "vertical" | "both";

export function useArrowNavigation<T extends HTMLElement>(
  orientation: Orientation = "both",
  loop: boolean = true
) {
  const containerRef = useRef<T>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!containerRef.current) return;

      const elements = Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(
          '[role="menuitem"], [role="option"], [role="tab"], button, a[href]'
        )
      ).filter(el => !el.hasAttribute("disabled"));

      if (elements.length === 0) return;

      const currentIndex = elements.findIndex((el) => el === document.activeElement);
      let nextIndex = currentIndex;

      const goNext = () => {
        nextIndex = currentIndex === elements.length - 1 ? (loop ? 0 : currentIndex) : currentIndex + 1;
      };

      const goPrev = () => {
        nextIndex = currentIndex <= 0 ? (loop ? elements.length - 1 : 0) : currentIndex - 1;
      };

      if (orientation === "horizontal" || orientation === "both") {
        if (e.key === "ArrowRight") goNext();
        if (e.key === "ArrowLeft") goPrev();
      }

      if (orientation === "vertical" || orientation === "both") {
        if (e.key === "ArrowDown") goNext();
        if (e.key === "ArrowUp") goPrev();
      }

      if (e.key === "Home") nextIndex = 0;
      if (e.key === "End") nextIndex = elements.length - 1;

      if (nextIndex !== currentIndex) {
        e.preventDefault();
        elements[nextIndex]?.focus();
      }
    },
    [orientation, loop]
  );

  return { containerRef, handleKeyDown };
}
