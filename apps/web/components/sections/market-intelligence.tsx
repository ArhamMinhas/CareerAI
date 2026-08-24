"use client";

import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";
import { cardHover, cn } from "@/lib/utils";

const demandData = [
  { month: "Jan", python: 62, rag: 18 },
  { month: "Mar", python: 66, rag: 27 },
  { month: "May", python: 69, rag: 38 },
  { month: "Jul", python: 71, rag: 49 },
  { month: "Sep", python: 74, rag: 58 },
  { month: "Nov", python: 78, rag: 66 },
];

export function MarketIntelligence() {
  // Recharts (v3) allocates its internal SVG element IDs via React's useId(), and
  // ResponsiveContainer only measures/renders its chart children once ResizeObserver is
  // available client-side — so the very first client render mounts a different number of
  // id-consuming elements than the server did. That offsets every useId() counter for
  // everything rendered after this section, corrupting unrelated hydration (e.g. the FAQ
  // accordion's ids) elsewhere on the page. Deferring the real chart to a post-mount render
  // keeps the server and first-client-render trees identical (both show the placeholder).
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <Section className="border-t border-border">
      <Container className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Built on what the job market actually wants.
          </h2>
          <p className="mt-4 max-w-[46ch] text-base leading-relaxed text-muted-foreground">
            Skill recommendations are weighted against real demand and growth trends, not a
            static list. When a skill starts showing up in more postings, your roadmap
            notices.
          </p>
        </Reveal>

        <Reveal delay={0.1}>
          <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
            <div className="h-64 w-full">
              {mounted && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={demandData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <XAxis
                      dataKey="month"
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
                      dataKey="python"
                      name="Python"
                      stroke="var(--color-muted-foreground)"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="rag"
                      name="RAG / LLM"
                      stroke="var(--color-primary)"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Illustrative demand trend, percentage of relevant postings mentioning each skill.
            </p>
          </div>
        </Reveal>
      </Container>
    </Section>
  );
}
