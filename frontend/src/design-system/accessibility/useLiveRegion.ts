import { useCallback, useEffect, useState } from "react";

type Politeness = "polite" | "assertive";

export function useLiveRegion(defaultPoliteness: Politeness = "polite") {
  const [message, setMessage] = useState("");
  const [politeness, setPoliteness] = useState<Politeness>(defaultPoliteness);

  const announce = useCallback((msg: string, politenessLevel?: Politeness) => {
    if (politenessLevel) setPoliteness(politenessLevel);
    // Briefly clear to force screen reader to re-announce if the message is the same
    setMessage("");
    setTimeout(() => {
      setMessage(msg);
    }, 50);
  }, []);

  useEffect(() => {
    // Check if the live region element exists; if not, create it
    let region = document.getElementById("a11y-live-region");
    if (!region) {
      region = document.createElement("div");
      region.id = "a11y-live-region";
      region.setAttribute("aria-live", defaultPoliteness);
      region.setAttribute("aria-atomic", "true");
      region.style.position = "absolute";
      region.style.width = "1px";
      region.style.height = "1px";
      region.style.padding = "0";
      region.style.margin = "-1px";
      region.style.overflow = "hidden";
      region.style.clip = "rect(0, 0, 0, 0)";
      region.style.whiteSpace = "nowrap";
      region.style.border = "0";
      document.body.appendChild(region);
    }
  }, [defaultPoliteness]);

  useEffect(() => {
    const region = document.getElementById("a11y-live-region");
    if (region) {
      region.setAttribute("aria-live", politeness);
      region.textContent = message;
    }
  }, [message, politeness]);

  return announce;
}
