"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ClientOnlyChart } from "@/components/charts/client-only-chart";
import type { SkillDemandPoint } from "@/lib/types/career-path";

/** docs/ML_PIPELINE.md §3 model 6, Phase 8 — real weekly `skill_demand` history plus the
 * trained model's next-period forecast, rendered as one continuous line. */
export function SkillDemandChart({
  history,
  forecast,
}: {
  history: SkillDemandPoint[];
  forecast: number | null;
}) {
  if (history.length === 0) return null;

  const data = history.map((point) => ({
    period: new Date(point.period).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    demand: point.demand_count,
    forecast: null as number | null,
  }));
  if (forecast !== null) {
    data.push({ period: "Next", demand: null as unknown as number, forecast });
    // Connects the last real point to the forecast point so the line doesn't have a gap.
    data[data.length - 2] = { ...data[data.length - 2], forecast: data[data.length - 2].demand };
  }

  return (
    <div className="h-56 w-full">
      <ClientOnlyChart
        fallback={<div className="h-full w-full animate-pulse rounded-lg bg-border/40" />}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <XAxis
              dataKey="period"
              stroke="var(--color-muted-foreground)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="var(--color-muted-foreground)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              width={32}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--color-background)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="demand"
              name="Postings mentioning this skill"
              stroke="var(--color-primary)"
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
            {forecast !== null ? (
              <Line
                type="monotone"
                dataKey="forecast"
                name="Forecast"
                stroke="var(--color-muted-foreground)"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 3 }}
                connectNulls
              />
            ) : null}
          </LineChart>
        </ResponsiveContainer>
      </ClientOnlyChart>
    </div>
  );
}
