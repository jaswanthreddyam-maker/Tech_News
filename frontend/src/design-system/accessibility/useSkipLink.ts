import { useCallback } from "react";

export function useSkipLink(targetId: string = "main-content") {
  const handleSkip = useCallback((e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      // Elements must have tabindex="-1" to receive programmatic focus if they aren't inherently focusable
      target.setAttribute("tabindex", "-1");
      target.focus();
      // Optionally remove it on blur to clean up
      target.addEventListener("blur", () => {
        target.removeAttribute("tabindex");
      }, { once: true });
    }
  }, [targetId]);

  return handleSkip;
}
