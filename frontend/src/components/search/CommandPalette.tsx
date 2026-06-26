"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { getCommands, registerBaseCommands } from "@/lib/commands/registry";
import { useAppStore } from "@/store/useStore";
import { sessionManager } from "@/lib/session/sessionManager";
import { useAnalytics } from "@/components/providers/AnalyticsProvider";
import { Search } from "lucide-react";
import { fetchKeywordSearch } from "@/lib/api/search/keyword";
import { KeywordSearchResult } from "@/lib/api/search/types";

export function CommandPalette({ onSelect }: { onSelect: () => void }) {
  const router = useRouter();
  const { setTheme } = useTheme();
  const { user, logoutUser } = useAppStore();
  const isAuthenticated = !!user;
  const { track } = useAnalytics();
  const [search, setSearch] = React.useState("");
  const [searchResults, setSearchResults] = React.useState<KeywordSearchResult[]>([]);
  const [isSearching, setIsSearching] = React.useState(false);

  React.useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    const timer = setTimeout(() => {
      fetchKeywordSearch(search, undefined, 5)
        .then(res => {
          setSearchResults(res || []);
          setIsSearching(false);
        })
        .catch(() => {
          setSearchResults([]);
          setIsSearching(false);
        });
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  React.useEffect(() => {
    // Re-register base commands to inject current dependencies
    registerBaseCommands({
      router,
      setTheme,
      isAuthenticated,
      logout: () => {
        sessionManager.logout();
        logoutUser();
      }
    });
  }, [router, setTheme, isAuthenticated, logoutUser]);

  const commands = getCommands();
  const groups = Array.from(new Set(commands.map(c => c.group)));

  const runCommand = React.useCallback((command: () => void, id: string) => {
    track("Search Executed", { commandId: id });
    command();
    onSelect();
  }, [onSelect, track]);

  return (
    <Command className="rounded-lg border shadow-md sm:max-w-2xl bg-background/95 backdrop-blur-xl h-full border-border/50">
      <CommandInput 
        placeholder="Type a command or search..." 
        value={search}
        onValueChange={setSearch}
      />
      <CommandList className="max-h-[60vh]">
        {search && searchResults.length === 0 && (
          <CommandEmpty>
            <div className="py-6 text-center text-sm">
              {isSearching ? (
                <p className="text-muted-foreground animate-pulse">Searching...</p>
              ) : (
                <p className="text-muted-foreground mb-4">No commands or articles found for &quot;{search}&quot;.</p>
              )}
            </div>
          </CommandEmpty>
        )}

        {searchResults.length > 0 && (
          <>
            <CommandGroup heading="Articles">
              {searchResults.map((result) => (
                <CommandItem
                  key={`article-${result.id}`}
                  value={`${result.title} ${search}`}
                  onSelect={() => {
                    track("Article Opened", { articleId: result.id });
                    router.push(`/articles/${result.id}`);
                    onSelect();
                  }}
                >
                  <Search className="mr-2 h-4 w-4 text-muted-foreground" />
                  <div className="flex flex-col">
                    <span className="line-clamp-1">{result.title}</span>
                    {result.description && <span className="text-xs text-muted-foreground line-clamp-1">{result.description}</span>}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}
        
        {/* Temporarily disabled suggestions group
        {!search && (
          <CommandGroup heading="Suggestions">
            <CommandItem
              onSelect={() => {
                track("Semantic Search Executed", { query: "AI News" });
                router.push(`/search?q=AI%20News`);
                onSelect();
              }}
            >
              <Search className="mr-2 h-4 w-4 text-primary" />
              <span>Explore AI News</span>
            </CommandItem>
          </CommandGroup>
        )}
        */}

        {groups.map(group => {
          const groupCommands = commands.filter(c => c.group === group);
          if (groupCommands.length === 0) return null;
          
          return (
            <React.Fragment key={group}>
              <CommandGroup heading={group}>
                {groupCommands.map(command => (
                  <CommandItem
                    key={command.id}
                    value={`${command.title} ${command.subtitle || ""} ${command.keywords?.join(" ") || ""}`}
                    disabled={command.disabled?.()}
                    onSelect={() => runCommand(command.action, command.id)}
                  >
                    {command.icon && <div className="mr-2 flex h-4 w-4 items-center justify-center text-muted-foreground">{command.icon}</div>}
                    <div className="flex flex-col">
                      <span>{command.title}</span>
                      {command.subtitle && <span className="text-xs text-muted-foreground">{command.subtitle}</span>}
                    </div>
                    {command.shortcut && (
                      <div className="ml-auto flex items-center gap-1">
                        {command.shortcut.map(key => (
                          <kbd key={key} className="bg-muted px-1.5 py-0.5 rounded border font-mono text-[10px] text-muted-foreground">
                            {key}
                          </kbd>
                        ))}
                      </div>
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
              <CommandSeparator />
            </React.Fragment>
          );
        })}
      </CommandList>
    </Command>
  );
}
