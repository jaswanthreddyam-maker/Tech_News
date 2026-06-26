import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

interface TelemetryMetricProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
  };
}

export function TelemetryMetric({ title, value, icon: Icon, trend }: TelemetryMetricProps) {
  return (
    <Card className="bg-surface shadow-soft border-border/50">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">{value}</div>
        {trend && (
          <p className="text-xs text-muted-foreground mt-1">
            <span className={trend.value >= 0 ? "text-success" : "text-destructive"}>
              {trend.value >= 0 ? "+" : ""}{trend.value}%
            </span>{" "}
            {trend.label}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
