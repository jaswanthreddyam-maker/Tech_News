import { useEffect, useCallback } from "react";

type KeyHandlerMap = {
  [key: string]: (e: KeyboardEvent) => void;
};

export function useKeyboardNavigation(
  handlers: KeyHandlerMap,
  isActive: boolean = true
) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isActive) return;
      const handler = handlers[e.key];
      if (handler) {
        handler(e);
      }
    },
    [handlers, isActive]
  );

  useEffect(() => {
    if (!isActive) return;
    
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown, isActive]);
}
