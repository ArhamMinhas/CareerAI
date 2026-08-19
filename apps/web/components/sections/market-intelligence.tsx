"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";

const demandData = [
  { month: "Jan", python: 62, rag: 18 },
  { month: "Mar", python: 66, rag: 27 },
  { month: "May", python: 69, rag: 38 },
  { month: "Jul", python: 71, rag: 49 },
  { month: "Sep", python: 74, rag: 58 },
  { month: "Nov", python: 78, rag: 66 },
];

export function MarketIntelligence() {
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
          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="h-64 w-full">
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
