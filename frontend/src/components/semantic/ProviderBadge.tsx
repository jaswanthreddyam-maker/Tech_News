import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Cpu } from "lucide-react";

interface ProviderBadgeProps {
  provider: string;
}

export function ProviderBadge({ provider }: ProviderBadgeProps) {
  // Common mapping for known providers
  let colorClass = "bg-secondary text-secondary-foreground";
  
  const p = provider.toLowerCase();
  if (p.includes("openai")) {
    colorClass = "bg-[#10a37f]/10 text-[#10a37f] border-[#10a37f]/20";
  } else if (p.includes("anthropic")) {
    colorClass = "bg-[#d97757]/10 text-[#d97757] border-[#d97757]/20";
  } else if (p.includes("gemini")) {
    colorClass = "bg-[#1a73e8]/10 text-[#1a73e8] border-[#1a73e8]/20";
  }

  return (
    <Badge variant="outline" className={`${colorClass} font-mono text-xs uppercase`}>
      <Cpu className="mr-1 h-3 w-3" />
      {provider}
    </Badge>
  );
}
