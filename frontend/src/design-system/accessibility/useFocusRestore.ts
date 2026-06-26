import { useEffect, useRef } from "react";

export function useFocusRestore(isActive: boolean = true) {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isActive) {
      // Store the currently focused element when the component mounts/becomes active
      previousFocusRef.current = document.activeElement as HTMLElement;
    } else if (previousFocusRef.current) {
      // Restore focus when it becomes inactive
      previousFocusRef.current.focus();
      previousFocusRef.current = null;
    }

    return () => {
      // Also restore focus on unmount if it was active
      if (isActive && previousFocusRef.current) {
        previousFocusRef.current.focus();
        previousFocusRef.current = null;
      }
    };
  }, [isActive]);
}
