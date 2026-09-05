"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3, Briefcase, FileText, Map, MessagesSquare, Target } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { ClientOnlyChart } from "@/components/charts/client-only-chart";
import { cardHover, cn } from "@/lib/utils";
import type {
  CandidateDashboard,
  MarketAnalytics,
  SkillAnalytics,
} from "@/lib/types/analytics";

type LoadState =
  | { kind: "loading" }
  | {
      kind: "loaded";
      dashboard: CandidateDashboard;
      market: MarketAnalytics;
      skills: SkillAnalytics;
    }
  | { kind: "error"; message: string };

export function AnalyticsView() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<CandidateDashboard>("/api/v1/analytics/dashboard"),
      apiFetch<MarketAnalytics>("/api/v1/analytics/market"),
      apiFetch<SkillAnalytics>("/api/v1/analytics/skills?sort=demand_count&limit=15"),
    ])
      .then(([dashboard, market, skills]) => {
        if (active) setState({ kind: "loaded", dashboard, market, skills });
      })
      .catch((err) => {
        if (!active) return;
        const message = err instanceof ApiError ? err.message : "Couldn't load analytics.";
        setState({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <div className="flex flex-col gap-6">
        <div className="h-32 animate-pulse rounded-xl border border-border bg-surface" />
        <div className="h-64 animate-pulse rounded-xl border border-border bg-surface" />
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="rounded-xl border border-danger/30 bg-surface p-6 text-center">
        <p className="text-sm text-danger">{state.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-medium text-foreground">My progress</h2>
        <MyProgress dashboard={state.dashboard} />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-medium text-foreground">Market intelligence</h2>
        <MarketIntelligence market={state.market} skills={state.skills} />
      </section>
    </div>
  );
}

function MyProgress({ dashboard }: { dashboard: CandidateDashboard }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <ProgressCard
        icon={FileText}
        title="Resume"
        value={
          dashboard.resume.overall_score !== null
            ? Math.round(dashboard.resume.overall_score).toString()
            : "—"
        }
        detail={
          dashboard.resume.status === "completed"
            ? "Latest score"
            : dashboard.resume.status === null
              ? "No resume analyzed yet"
              : `Status: ${dashboard.resume.status}`
        }
        href="/dashboard/resume"
      />
      <ProgressCard
        icon={Target}
        title="Skill gaps"
        value={dashboard.skill_gaps ? String(dashboard.skill_gaps.missing) : "—"}
        detail={
          dashboard.skill_gaps
            ? `missing for ${dashboard.skill_gaps.target_role}`
            : "Set a target role to see gaps"
        }
        href="/dashboard/skill-gap"
      />
      <ProgressCard
        icon={MessagesSquare}
        title="Interviews"
        value={String(dashboard.interviews.total_completed)}
        detail={
          dashboard.interviews.average_overall_score !== null
            ? `avg score ${Math.round(dashboard.interviews.average_overall_score)}`
            : "completed sessions"
        }
        href="/dashboard/interviews"
      />
      <ProgressCard
        icon={Map}
        title="Roadmap"
        value={
          dashboard.roadmap
            ? `${dashboard.roadmap.completed_items}/${dashboard.roadmap.total_items}`
            : "—"
        }
        detail={dashboard.roadmap ? dashboard.roadmap.target_role : "No roadmap yet"}
        href="/dashboard/roadmap"
      />
      <div
        className={cn(
          cardHover,
          "flex flex-col gap-3 rounded-xl border border-border bg-surface p-5 sm:col-span-2 lg:col-span-4"
        )}
      >
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Briefcase className="size-4 text-muted-foreground" strokeWidth={1.75} />
          Job search funnel
        </div>
        <div className="flex flex-wrap gap-6">
          <Stat label="Matches" value={dashboard.applications.total_matches} />
          <Stat label="Saved" value={dashboard.applications.saved} />
          <Stat label="Applied" value={dashboard.applications.applied} />
          <Stat label="Interviewing" value={dashboard.applications.interviewing} />
          <Stat label="Offer" value={dashboard.applications.offer} />
          <Stat label="Rejected" value={dashboard.applications.rejected} />
        </div>
      </div>
    </div>
  );
}

function ProgressCard({
  icon: Icon,
  title,
  value,
  detail,
  href,
}: {
  icon: typeof FileText;
  title: string;
  value: string;
  detail: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        cardHover,
        "flex flex-col gap-2 rounded-xl border border-border bg-surface p-5"
      )}
    >
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Icon className="size-3.5" strokeWidth={1.75} />
        {title}
      </div>
      <p className="text-2xl font-semibold tracking-tight text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground">{detail}</p>
    </Link>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-lg font-semibold tracking-tight text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function MarketIntelligence({
  market,
  skills,
}: {
  market: MarketAnalytics;
  skills: SkillAnalytics;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
          <h3 className="text-sm font-medium text-foreground">Job postings, by week</h3>
          <div className="mt-4 h-56 w-full">
            <ClientOnlyChart
              fallback={<div className="h-full w-full animate-pulse rounded-lg bg-border/40" />}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={market.job_posting_trend.map((p) => ({
                    period: new Date(p.period).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    }),
                    total: p.total,
                  }))}
                  margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
                >
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
                    dataKey="total"
                    name="Active postings"
                    stroke="var(--color-primary)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ClientOnlyChart>
          </div>
        </div>

        <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
          <h3 className="text-sm font-medium text-foreground">Median salary, by week</h3>
          <div className="mt-4 h-56 w-full">
            <ClientOnlyChart
              fallback={<div className="h-full w-full animate-pulse rounded-lg bg-border/40" />}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={market.salary_trend.map((p) => ({
                    period: new Date(p.period).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    }),
                    average_p50: Math.round(p.average_p50),
                  }))}
                  margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
                >
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
                    width={48}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-background)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(value) => [
                      `$${Number(Array.isArray(value) ? value[0] : value).toLocaleString()}`,
                      "Median salary",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="average_p50"
                    name="Median salary"
                    stroke="var(--color-primary)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ClientOnlyChart>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
          <h3 className="text-sm font-medium text-foreground">Top growing skills</h3>
          {market.top_growing_skills.length === 0 ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Not enough recent data to rank trending skills yet.
            </p>
          ) : (
            <ul className="mt-3 flex flex-col divide-y divide-border">
              {market.top_growing_skills.map((skill) => (
                <li key={skill.skill_id} className="flex items-center justify-between py-2.5">
                  <Link
                    href={`/skills/${skill.skill_slug}`}
                    className="text-sm text-foreground transition-colors hover:text-primary"
                  >
                    {skill.skill_name}
                  </Link>
                  <span className="text-xs font-medium text-success">
                    +{Math.round(skill.growth_rate * 100)}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
          <h3 className="text-sm font-medium text-foreground">Trending career paths</h3>
          {market.trending_career_paths.length === 0 ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Not enough recent data to rank career paths yet.
            </p>
          ) : (
            <ul className="mt-3 flex flex-col divide-y divide-border">
              {market.trending_career_paths.map((path) => (
                <li key={path.career_path_id} className="flex items-center justify-between py-2.5">
                  <Link
                    href={`/careers/${path.career_path_slug}`}
                    className="text-sm text-foreground transition-colors hover:text-primary"
                  >
                    {path.career_path_title}
                  </Link>
                  {path.growth_rate !== null ? (
                    <span className="text-xs font-medium text-success">
                      +{Math.round(path.growth_rate * 100)}%
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <BarChart3 className="size-4 text-muted-foreground" strokeWidth={1.75} />
          Skill demand table
        </div>
        {skills.rows.length === 0 ? (
          <p className="mt-3 text-xs text-muted-foreground">No skill data yet.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Skill</th>
                  <th className="py-2 pr-4 font-medium">Demand</th>
                  <th className="py-2 pr-4 font-medium">Growth</th>
                  <th className="py-2 font-medium">Avg. associated salary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {skills.rows.map((row) => (
                  <tr key={row.skill_id}>
                    <td className="py-2 pr-4">
                      <Link
                        href={`/skills/${row.skill_slug}`}
                        className="text-foreground transition-colors hover:text-primary"
                      >
                        {row.skill_name}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {row.demand_count ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {row.growth_rate !== null ? `${Math.round(row.growth_rate * 100)}%` : "—"}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {row.avg_associated_salary !== null
                        ? `$${Math.round(row.avg_associated_salary).toLocaleString()}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
