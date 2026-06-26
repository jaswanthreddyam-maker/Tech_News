"use client";

import React from "react";
import {
  Share2,
  Bookmark,
  BookmarkCheck,
  Copy,
  Printer,
  FolderPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api/client";
import { m, useReducedMotion } from "framer-motion";
import { MotionScales } from "@/design-system/motion/tokens";

interface FloatingActionsProps {
  url: string;
  title: string;
  articleId?: string;
}

/** Theme-aware icon button class — works in both light and dark mode */
const iconBtnClass =
  "w-10 h-10 rounded-full transition-all duration-150 " +
  "text-muted-foreground " +
  "hover:text-foreground hover:bg-foreground/10 " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2";

export function FloatingActions({ url, title, articleId }: FloatingActionsProps) {
  const { toast } = useToast();
  const [isSaved, setIsSaved] = React.useState(false);
  const shouldReduceMotion = useReducedMotion();

  React.useEffect(() => {
    if (articleId) {
      apiFetch<string[]>("/me/saved")
        .then((res) => {
          setIsSaved(res.includes(articleId));
        })
        .catch(() => {
          // Silently fail — user may not be logged in
        });
    }
  }, [articleId]);

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch {
        // User cancelled — do nothing
      }
    } else {
      await handleCopy();
    }
  };

  const handleSave = async () => {
    if (!articleId) {
      toast({ title: "Cannot save", description: "Article ID not found." });
      return;
    }
    try {
      const res = await apiFetch<{ active: boolean }>(`/me/saved/${articleId}`, {
        method: "POST",
      });
      setIsSaved(res.active);
      toast({
        title: res.active ? "Bookmarked" : "Bookmark removed",
        description: res.active
          ? "Article saved to your profile."
          : "Article removed from saved list.",
      });
    } catch {
      // Optimistic local toggle as fallback
      const next = !isSaved;
      setIsSaved(next);
      toast({
        title: next ? "Bookmarked locally" : "Bookmark removed",
        description: next
          ? "Saved locally — sign in to sync across devices."
          : "Removed from bookmarks.",
      });
    }
  };

  const handleWorkspace = async () => {
    if (!articleId) {
      toast({ title: "Cannot add", description: "Article ID not found." });
      return;
    }
    try {
      const res: any[] = await apiFetch("/workspaces");
      let ws = res.length > 0 ? res[0] : null;

      if (!ws) {
        ws = await apiFetch("/workspaces", {
          method: "POST",
          body: JSON.stringify({
            name: "My Workspace",
            description: "Automatically created",
          }),
        });
      }

      await apiFetch(`/workspaces/${ws.id}/articles`, {
        method: "POST",
        body: JSON.stringify({ article_id: articleId }),
      });

      toast({
        title: "Added to Workspace",
        description: `Article pinned to "${ws.name}".`,
      });
    } catch {
      toast({
        title: "Workspace",
        description: "Coming soon — workspace sync is not yet available.",
      });
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      toast({
        title: "Link copied",
        description: "Article link copied to clipboard.",
      });
    } catch {
      toast({
        variant: "destructive",
        title: "Copy failed",
        description: "Please copy the URL manually from the address bar.",
      });
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const SaveIcon = isSaved ? BookmarkCheck : Bookmark;

  const toolbarVariants = {
    hidden: shouldReduceMotion ? { opacity: 0 } : { opacity: 0, x: -12, y: 24 },
    visible: {
      opacity: 1,
      x: 0,
      y: 0,
      transition: {
        duration: shouldReduceMotion ? 0.15 : 0.75,
        ease: (shouldReduceMotion ? "linear" : [0.22, 1, 0.36, 1]) as any,
        delay: 0.25,
      },
    },
  };

  return (
    <>
      {/* ── Desktop Floating Sidebar ── */}
      <m.aside
        initial={false}
        animate="visible"
        variants={toolbarVariants}
        className="hidden xl:flex flex-col items-center gap-4 sticky top-32 h-fit w-16 shrink-0"
        aria-label="Article actions"
      >
        <div className="flex flex-col gap-3 p-3 rounded-full bg-background/80 border border-border backdrop-blur shadow-sm">
          <Button variant="ghost" size="icon" className={iconBtnClass} asChild>
            <m.button
              onClick={handleShare}
              aria-label="Share article"
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
            >
              <Share2 className="w-4 h-4" />
            </m.button>
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className={[
              iconBtnClass,
              isSaved
                ? "text-primary bg-primary/10 hover:bg-primary/20 hover:text-primary"
                : "",
            ].join(" ")}
            asChild
          >
            <m.button
              onClick={handleSave}
              aria-label={isSaved ? "Remove bookmark" : "Bookmark article"}
              aria-pressed={isSaved}
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
            >
              <SaveIcon className="w-4 h-4" />
            </m.button>
          </Button>

          {/* Temporarily disabled workspace action
          <Button variant="ghost" size="icon" className={iconBtnClass} asChild>
            <m.button
              onClick={handleWorkspace}
              aria-label="Add to workspace"
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
            >
              <FolderPlus className="w-4 h-4" />
            </m.button>
          </Button>
          */}

          <Button variant="ghost" size="icon" className={iconBtnClass} asChild>
            <m.button
              onClick={handleCopy}
              aria-label="Copy article link"
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
            >
              <Copy className="w-4 h-4" />
            </m.button>
          </Button>

          <div className="w-full h-px bg-border/60 my-0.5" role="separator" />

          <Button variant="ghost" size="icon" className={iconBtnClass} asChild>
            <m.button
              onClick={handlePrint}
              aria-label="Print article"
              whileHover={{ scale: MotionScales.hover }}
              whileTap={{ scale: MotionScales.tap }}
            >
              <Printer className="w-4 h-4" />
            </m.button>
          </Button>
        </div>
      </m.aside>

      {/* ── Mobile Sticky Bottom Bar ── */}
      <m.div
        initial={false}
        animate="visible"
        variants={toolbarVariants}
        className="xl:hidden fixed bottom-0 left-0 w-full z-50 bg-background/90 backdrop-blur-md border-t border-border px-4 py-3 pb-safe flex justify-around items-center shadow-[0_-4px_24px_hsl(var(--border)/0.5)]"
        role="toolbar"
        aria-label="Article actions"
      >
        <Button
          variant="ghost"
          size="sm"
          className="flex flex-col gap-1 text-muted-foreground hover:text-foreground hover:bg-foreground/10 h-auto py-2 rounded-xl transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          asChild
        >
          <m.button
            onClick={handleShare}
            aria-label="Share"
            whileHover={{ scale: MotionScales.hover }}
            whileTap={{ scale: MotionScales.tap }}
          >
            <Share2 className="w-5 h-5" />
            <span className="text-[10px] uppercase font-mono tracking-wider">Share</span>
          </m.button>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className={[
            "flex flex-col gap-1 h-auto py-2 rounded-xl transition-all",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring",
            isSaved
              ? "text-primary hover:text-primary hover:bg-primary/10"
              : "text-muted-foreground hover:text-foreground hover:bg-foreground/10",
          ].join(" ")}
          asChild
        >
          <m.button
            onClick={handleSave}
            aria-label={isSaved ? "Remove bookmark" : "Bookmark"}
            aria-pressed={isSaved}
            whileHover={{ scale: MotionScales.hover }}
            whileTap={{ scale: MotionScales.tap }}
          >
            <SaveIcon className="w-5 h-5" />
            <span className="text-[10px] uppercase font-mono tracking-wider">
              {isSaved ? "Saved" : "Save"}
            </span>
          </m.button>
        </Button>

        {/* Temporarily disabled workspace action
        <Button
          variant="ghost"
          size="sm"
          className="flex flex-col gap-1 text-muted-foreground hover:text-foreground hover:bg-foreground/10 h-auto py-2 rounded-xl transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          asChild
        >
          <m.button
            onClick={handleWorkspace}
            aria-label="Add to workspace"
            whileHover={{ scale: MotionScales.hover }}
            whileTap={{ scale: MotionScales.tap }}
          >
            <FolderPlus className="w-5 h-5" />
            <span className="text-[10px] uppercase font-mono tracking-wider">Workspace</span>
          </m.button>
        </Button>
        */}

        <Button
          variant="ghost"
          size="sm"
          className="flex flex-col gap-1 text-muted-foreground hover:text-foreground hover:bg-foreground/10 h-auto py-2 rounded-xl transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
          asChild
        >
          <m.button
            onClick={handleCopy}
            aria-label="Copy link"
            whileHover={{ scale: MotionScales.hover }}
            whileTap={{ scale: MotionScales.tap }}
          >
            <Copy className="w-5 h-5" />
            <span className="text-[10px] uppercase font-mono tracking-wider">Copy</span>
          </m.button>
        </Button>
      </m.div>
    </>
  );
}
