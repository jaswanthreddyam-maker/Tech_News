function generateUUID() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function getAnonymousId(): string | null {
  if (typeof window === "undefined") return null;
  let anonId = localStorage.getItem("tnt_anon_id");
  if (!anonId) {
    anonId = generateUUID();
    localStorage.setItem("tnt_anon_id", anonId);
  }
  return anonId;
}
