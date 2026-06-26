export function getHealthColor(status?: string): { dotColor: string, textColor: string } {
  const normStatus = (status || "UNKNOWN").toUpperCase();

  switch (normStatus) {
    case "ONLINE":
      return {
        dotColor: "bg-emerald-500",
        textColor: "text-emerald-400",
      };
    case "DELAYED":
      return {
        dotColor: "bg-orange-500",
        textColor: "text-orange-400",
      };
    case "DEGRADED":
      return {
        dotColor: "bg-amber-500",
        textColor: "text-amber-400",
      };
    case "OFFLINE":
    case "ERROR":
      return {
        dotColor: "bg-red-500",
        textColor: "text-red-500",
      };
    case "UNKNOWN":
    default:
      return {
        dotColor: "bg-[#888]",
        textColor: "text-[#888]",
      };
  }
}

export function getHealthLabel(status?: string): string {
  return (status || "UNKNOWN").toUpperCase();
}
