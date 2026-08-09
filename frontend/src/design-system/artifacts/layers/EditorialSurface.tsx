import React from 'react';
import { ContentTitle, ContentSummary, ContentSource, ContentDate, ContentThumbnail } from './EditorialContent';
import { Eye, Clock } from 'lucide-react';

interface EditorialSurfaceProps {
  article: any;
  variant: 'feature' | 'compact';
  isHovered: boolean;
}

function getReasonText(reason: any): string | null {
  if (!reason) return null;
  if (typeof reason === 'string') return reason;
  if (typeof reason === 'object') {
    return reason.message || reason.label || reason.text || null;
  }
  return null;
}

export function EditorialSurface({ article, variant, isHovered }: EditorialSurfaceProps) {
  const reasonText = getReasonText(article.reason);
  
  if (variant === 'feature') {
    return (
      <div 
        className="relative z-30 w-full h-full flex flex-col"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Dominant Hero Photography — fills the top ~55% */}
        <div 
          style={{ transform: 'translateZ(8px)', transformStyle: 'preserve-3d' }} 
          className="w-full relative overflow-hidden rounded-t-[13px]"
        >
          <ContentThumbnail 
            article={article} 
            className="aspect-[16/10] w-full overflow-hidden bg-muted/20" 
          />
          {/* Bottom gradient fade into typography area */}
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-[#121318] to-transparent pointer-events-none" />
        </div>
        
        {/* Typography Grid — fills the bottom ~45% */}
        <div className="px-5 pb-4 pt-2 flex flex-col justify-between flex-1" style={{ transformStyle: 'preserve-3d' }}>
          <div>
            <div style={{ transform: 'translateZ(4px)' }} className="mb-1.5">
              <ContentSource 
                source={article.source_name || article.source || 'Network'} 
                className="text-[10px] font-mono uppercase tracking-widest text-primary font-semibold"
              />
            </div>
            
            <div style={{ transform: 'translateZ(12px)' }} className="mb-2">
              <ContentTitle 
                title={article.title} 
                className="text-xl sm:text-[22px] font-serif font-bold text-foreground leading-snug group-hover:text-white transition-colors duration-300 drop-shadow-md line-clamp-3"
              />
            </div>
            
            <div style={{ transform: 'translateZ(6px)' }}>
              <ContentSummary 
                summary={article.summary} 
                className="text-muted-foreground text-xs sm:text-[13px] line-clamp-2 sm:line-clamp-3 leading-relaxed"
              />
            </div>
          </div>

          {/* Metadata Rail */}
          <div className="mt-3 pt-2 flex items-center justify-between opacity-70" style={{ transformStyle: 'preserve-3d' }}>
            <div style={{ transform: 'translateZ(4px)' }} className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-widest font-mono">
              <Clock className="w-3 h-3" />
              {article.published_at ? <ContentDate date={article.published_at} /> : <span>Just Now</span>}
            </div>
            {reasonText && (
              <div style={{ transform: 'translateZ(4px)' }} className={`flex items-center gap-1 text-[10px] font-mono ${isHovered ? 'text-primary' : 'text-muted-foreground'}`}>
                <Eye className="w-3 h-3 shrink-0" />
                <span className="line-clamp-1">{reasonText}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Compact Variant — dense editorial plaque
  return (
    <div 
      className="relative z-30 w-full h-full flex p-3 sm:p-3.5 gap-3 items-center"
      style={{ transformStyle: 'preserve-3d' }}
    >
      {/* Typography */}
      <div className="flex flex-col min-h-0 flex-1 justify-center overflow-hidden" style={{ transformStyle: 'preserve-3d' }}>
        <div style={{ transform: 'translateZ(4px)' }} className="mb-0.5">
          <ContentSource 
            source={article.source_name || article.source || 'Network'} 
            className="text-[10px] font-mono uppercase tracking-widest text-primary font-semibold"
          />
        </div>
        
        <div style={{ transform: 'translateZ(8px)' }} className="mb-1 overflow-hidden">
          <ContentTitle 
            title={article.title} 
            className="font-serif font-bold text-xs sm:text-sm leading-snug group-hover:text-white transition-colors duration-300 line-clamp-2"
          />
        </div>
        
        <div className="flex items-center gap-2 min-h-0 shrink-0 opacity-60" style={{ transformStyle: 'preserve-3d' }}>
          <div style={{ transform: 'translateZ(4px)' }} className="flex items-center gap-1 text-[9px] text-muted-foreground uppercase tracking-widest font-mono">
            <Clock className="w-2.5 h-2.5" />
            {article.published_at ? <ContentDate date={article.published_at} /> : <span>Just Now</span>}
          </div>
          {reasonText && (
            <div style={{ transform: 'translateZ(4px)' }} className={`text-[9px] font-mono line-clamp-1 flex items-center gap-1 ${isHovered ? 'text-primary' : 'text-muted-foreground'}`}>
              <Eye className="w-2.5 h-2.5 shrink-0" />
              <span>{reasonText}</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Thumbnail */}
      <div 
        style={{ transform: 'translateZ(6px)' }}
        className="shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-[8px] overflow-hidden bg-muted/10"
      >
        <ContentThumbnail 
          article={article} 
          className="w-full h-full overflow-hidden bg-muted/20" 
        />
      </div>
    </div>
  );
}
