import { useEffect } from "react";
import { useFocusTrap } from "./useFocusTrap";
import { useFocusRestore } from "./useFocusRestore";

export function useAccessibleDialog(isOpen: boolean, onClose: () => void) {
  const containerRef = useFocusTrap(isOpen);
  useFocusRestore(isOpen);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  return containerRef;
}
