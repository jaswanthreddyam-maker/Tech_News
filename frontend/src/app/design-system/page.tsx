"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SentimentBadge } from "@/components/semantic/SentimentBadge";
import { ClusterBadge } from "@/components/semantic/ClusterBadge";
import { SemanticScore } from "@/components/semantic/SemanticScore";
import { ProviderBadge } from "@/components/semantic/ProviderBadge";
import { ConfidenceIndicator } from "@/components/semantic/ConfidenceIndicator";
import { AISummary } from "@/components/semantic/AISummary";
import { TelemetryMetric } from "@/components/semantic/TelemetryMetric";
import { Activity, Cpu, Database, Server } from "lucide-react";

export default function DesignSystemPage() {
  return (
    <div className="container mx-auto p-8 space-y-16">
      <div className="space-y-4">
        <h1 className="text-4xl font-serif font-black tracking-tight">Design System</h1>
        <p className="text-xl text-muted-foreground">The foundational design language and UI primitives for Tech News Today.</p>
      </div>

      <section className="space-y-6">
        <h2 className="text-2xl font-serif font-bold border-b border-border pb-2">1. Typography</h2>
        <div className="grid gap-6">
          <div>
            <span className="text-sm text-muted-foreground block mb-1">Font Sans (Inter) - UI & Data</span>
            <p className="font-sans text-lg">The quick brown fox jumps over the lazy dog.</p>
          </div>
          <div>
            <span className="text-sm text-muted-foreground block mb-1">Font Serif (Merriweather) - Editorial</span>
            <p className="font-serif text-2xl font-bold">The quick brown fox jumps over the lazy dog.</p>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-serif font-bold border-b border-border pb-2">2. Color Tokens</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <ColorSwatch name="Background" bgClass="bg-background" />
          <ColorSwatch name="Surface" bgClass="bg-surface" />
          <ColorSwatch name="Card" bgClass="bg-card" />
          <ColorSwatch name="Primary" bgClass="bg-primary" textClass="text-primary-foreground" />
          <ColorSwatch name="Accent" bgClass="bg-accent" textClass="text-accent-foreground" />
          <ColorSwatch name="Success" bgClass="bg-success" textClass="text-success-foreground" />
          <ColorSwatch name="Warning" bgClass="bg-warning" textClass="text-warning-foreground" />
          <ColorSwatch name="Destructive" bgClass="bg-destructive" textClass="text-destructive-foreground" />
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-serif font-bold border-b border-border pb-2">3. Buttons & Inputs</h2>
        <div className="flex flex-wrap items-center gap-4">
          <Button>Primary Button</Button>
          <Button variant="secondary">Secondary Button</Button>
          <Button variant="outline">Outline Button</Button>
          <Button variant="ghost">Ghost Button</Button>
          <Button variant="destructive">Destructive</Button>
        </div>
        <div className="grid max-w-sm gap-4">
          <Input placeholder="Search articles..." />
          <Textarea placeholder="Type your comment here." />
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-serif font-bold border-b border-border pb-2">4. AI & Semantic Primitives</h2>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Badges & Indicators</h3>
            <div className="flex flex-wrap gap-3">
              <SentimentBadge sentiment="positive" score={0.92} />
              <SentimentBadge sentiment="negative" score={0.88} />
              <SentimentBadge sentiment="neutral" />
            </div>
            <div className="flex flex-wrap gap-3">
              <ClusterBadge clusterId={42} clusterSize={15} />
              <ClusterBadge clusterId={7} />
            </div>
            <div className="flex flex-wrap gap-3">
              <ProviderBadge provider="OpenAI" />
              <ProviderBadge provider="Anthropic" />
              <ProviderBadge provider="Gemini" />
            </div>
            <div className="flex flex-wrap gap-3">
              <ConfidenceIndicator confidence={0.95} />
              <ConfidenceIndicator confidence={0.75} />
              <ConfidenceIndicator confidence={0.45} />
            </div>
            <div className="pt-2">
              <SemanticScore score={0.85} />
            </div>
            <div className="pt-2">
              <SemanticScore score={0.45} />
            </div>
          </div>
          
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Content Blocks</h3>
            <AISummary 
              provider="OpenAI GPT-4o"
              summary="NVIDIA has announced its next-generation Blackwell architecture, promising a 30x performance increase in LLM inference workloads while significantly reducing energy consumption." 
            />
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-serif font-bold border-b border-border pb-2">5. Telemetry & Dashboards</h2>
        <div className="grid md:grid-cols-4 gap-4">
          <TelemetryMetric title="Active Users" value="12,304" icon={Activity} trend={{ value: 12, label: "from last week" }} />
          <TelemetryMetric title="Articles Processed" value="1.2M" icon={Database} trend={{ value: 4, label: "from yesterday" }} />
          <TelemetryMetric title="API Latency" value="142ms" icon={Server} trend={{ value: -15, label: "from average" }} />
          <TelemetryMetric title="GPU Usage" value="84%" icon={Cpu} trend={{ value: 5, label: "vs baseline" }} />
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-serif font-bold border-b border-border pb-2">6. Loading States</h2>
        <div className="space-y-3">
          <Skeleton className="h-4 w-[250px]" />
          <Skeleton className="h-4 w-[200px]" />
          <Skeleton className="h-12 w-full" />
        </div>
      </section>

    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ColorSwatch({ name, bgClass, textClass = "text-foreground" }: { name: string, bgClass: string, textClass?: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className={`h-24 rounded-card border shadow-sm ${bgClass}`} />
      <div>
        <div className="font-medium text-sm">{name}</div>
        <div className="text-xs text-muted-foreground font-mono">{bgClass.replace('bg-', '')}</div>
      </div>
    </div>
  );
}
