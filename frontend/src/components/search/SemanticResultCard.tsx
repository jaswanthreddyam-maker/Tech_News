import Link from "next/link";
import { m } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";
import { SemanticSearchResult } from "@/lib/api/search/types";
import { formatDistanceToNow } from "date-fns";
import { Building2, Tag, FileText } from "lucide-react";

interface Props {
  result: SemanticSearchResult;
}

export function SemanticResultCard({ result }: Props) {
  const publishedStr = result.date 
    ? formatDistanceToNow(new Date(result.date), { addSuffix: true })
    : "";

  let icon = <FileText className="w-5 h-5 text-blue-500" />;
  let href = `/articles/${result.id}`;
  
  if (result.type === "entity") {
    icon = <Building2 className="w-5 h-5 text-emerald-500" />;
    href = `/entities/${result.id}`;
  } else if (result.type === "topic") {
    icon = <Tag className="w-5 h-5 text-purple-500" />;
    href = `/topics/${result.id}`;
  }

  return (
    <m.div 
      whileHover={{ scale: MotionScales.card }}
      whileTap={{ scale: MotionScales.tap }}
      className="flex flex-col md:flex-row gap-6 p-4 md:p-6 rounded-xl border border-border/50 bg-card/30 hover:bg-card/50 transition-colors group"
    >
      {/* Content Side */}
      <div className="flex-1 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {icon}
            <span className="text-xs uppercase tracking-wider font-mono text-muted-foreground">{result.type}</span>
          </div>
          {publishedStr && <span className="text-xs text-muted-foreground font-mono">{publishedStr}</span>}
        </div>
        
        <div>
          <Link href={href} className="group-hover:text-primary transition-colors">
            <h3 className="text-xl font-bold leading-tight mb-2">{result.title}</h3>
          </Link>
          <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
            {result.description}
          </p>
        </div>
      </div>
    </m.div>
  );
}
