"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { RefreshCw, Sparkles, ChevronDown } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { CareerGoal } from "@/lib/types/profile";
import type { CareerPath, GapLevel, SkillGapsResponse } from "@/lib/types/career-path";

const GAP_LEVEL_META: Record<GapLevel, { label: string; text: string; bar: string; dot: string }> = {
  missing: { label: "Missing", text: "text-danger", bar: "bg-danger", dot: "bg-danger" },
  weak: { label: "Weak", text: "text-warning", bar: "bg-warning", dot: "bg-warning" },
  adequate: { label: "Adequate", text: "text-primary", bar: "bg-primary", dot: "bg-primary" },
  strong: { label: "Strong", text: "text-success", bar: "bg-success", dot: "bg-success" },
};

const MAX_PRIORITY = 20; // weight(10) * core-multiplier(2) — see app/services/skill_gap.py

type GapsResult =
  | { targetRole: string; kind: "loaded"; data: SkillGapsResponse }
  | { targetRole: string; kind: "error"; message: string };

export function SkillGapView() {
  const [careerPaths, setCareerPaths] = useState<CareerPath[] | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [gapsResult, setGapsResult] = useState<GapsResult | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Load the career-path catalog once, and pick a sensible default target role from the
  // user's active career goal if it happens to match a curated path.
  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<CareerPath[]>("/api/v1/careers"),
      apiFetch<CareerGoal[]>("/api/v1/career-goals").catch(() => []),
    ])
      .then(([paths, careerGoals]) => {
        if (!active) return;
        setCareerPaths(paths);
        const activeGoal = careerGoals.find((goal) => goal.is_active);
        const matched = activeGoal
          ? paths.find((cp) => cp.title.toLowerCase() === activeGoal.target_role.toLowerCase())
          : undefined;
        if (matched) setTargetRole(matched.slug);
      })
      .catch(() => {
        if (active) setCareerPaths([]);
      });
    return () => {
      active = false;
    };
  }, []);

  // Fetch gaps whenever the selected target role changes. Loading state is derived at render
  // time (below) by comparing `gapsResult`'s role to the current selection, rather than an
  // explicit "loading" setState at the top of this effect before the await settles.
  useEffect(() => {
    if (!targetRole) return;
    let active = true;
    apiFetch<SkillGapsResponse>(`/api/v1/skills/gaps?target_role=${encodeURIComponent(targetRole)}`)
      .then((data) => {
        if (active) setGapsResult({ targetRole, kind: "loaded", data });
      })
      .catch((err) => {
        if (!active) return;
        const message = err instanceof ApiError ? err.message : "Couldn't load skill gaps.";
        setGapsResult({ targetRole, kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, [targetRole]);

  async function handleRefresh() {
    if (!targetRole) return;
    setRefreshing(true);
    try {
      const data = await apiFetch<SkillGapsResponse>(
        `/api/v1/skills/gaps/refresh?target_role=${encodeURIComponent(targetRole)}`,
        { method: "POST" }
      );
      setGapsResult({ targetRole, kind: "loaded", data });
    } catch {
      // Keep showing the last-known-good data; refreshing is best-effort.
    } finally {
      setRefreshing(false);
    }
  }

  const isLoadingCatalog = careerPaths === null;
  const isLoadingGaps = targetRole !== "" && gapsResult?.targetRole !== targetRole;
  const currentResult = gapsResult?.targetRole === targetRole ? gapsResult : null;

  return (
    <div className="flex flex-col gap-6">
      <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-foreground">Target role</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Pick a curated career path to compare your skills against.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <RoleSelect
              careerPaths={careerPaths ?? []}
              value={targetRole}
              onChange={setTargetRole}
              disabled={isLoadingCatalog}
            />
            {currentResult?.kind === "loaded" ? (
              <button
                type="button"
                onClick={handleRefresh}
                disabled={refreshing}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border-strong px-3 text-xs font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-background disabled:opacity-50"
              >
                <RefreshCw className={cn("size-3.5", refreshing && "animate-spin")} strokeWidth={1.75} />
                Refresh
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {isLoadingCatalog || isLoadingGaps ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
          >
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-xl border border-border bg-surface" />
            ))}
          </motion.div>
        ) : !targetRole ? (
          <motion.div
            key="no-target"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={cn(
              cardHover,
              "flex flex-col items-center gap-2 rounded-xl border border-border bg-surface px-6 py-14 text-center"
            )}
          >
            <Sparkles className="size-6 text-muted-foreground" strokeWidth={1.5} />
            <h3 className="mt-2 text-sm font-medium text-foreground">Pick a target role above</h3>
            <p className="max-w-[40ch] text-sm text-muted-foreground">
              We&apos;ll compare your profile&apos;s skills against that role&apos;s
              required-skill profile and show exactly what to work on next.
            </p>
          </motion.div>
        ) : currentResult?.kind === "error" ? (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={cn(cardHover, "rounded-xl border border-danger/30 bg-surface p-6 text-center")}
          >
            <p className="text-sm text-danger">{currentResult.message}</p>
          </motion.div>
        ) : currentResult?.kind === "loaded" ? (
          <motion.div
            key="loaded"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex flex-col gap-6"
          >
            <SummaryTiles summary={currentResult.data.summary} />
            {currentResult.data.recommended_next.length > 0 ? (
              <RecommendedNext items={currentResult.data.recommended_next} />
            ) : null}
            <FullBreakdown items={currentResult.data.gaps} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function RoleSelect({
  careerPaths,
  value,
  onChange,
  disabled,
}: {
  careerPaths: CareerPath[];
  value: string;
  onChange: (slug: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 appearance-none rounded-lg border border-border-strong bg-background pl-3 pr-8 text-xs font-medium text-foreground outline-none transition-colors duration-200 hover:border-primary/40 disabled:opacity-50"
      >
        <option value="" disabled>
          Select a role…
        </option>
        {careerPaths.map((cp) => (
          <option key={cp.slug} value={cp.slug}>
            {cp.title}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
        strokeWidth={1.75}
      />
    </div>
  );
}

function SummaryTiles({ summary }: { summary: SkillGapsResponse["summary"] }) {
  const tiles: { level: GapLevel; count: number }[] = [
    { level: "missing", count: summary.missing },
    { level: "weak", count: summary.weak },
    { level: "adequate", count: summary.adequate },
    { level: "strong", count: summary.strong },
  ];
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {tiles.map((tile, i) => {
        const meta = GAP_LEVEL_META[tile.level];
        return (
          <motion.div
            key={tile.level}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className={cn(cardHover, "rounded-xl border border-border bg-surface p-5")}
          >
            <span className={cn("inline-block size-2 rounded-full", meta.dot)} />
            <p className="mt-3 text-2xl font-semibold tracking-tight text-foreground">
              {tile.count}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">{meta.label}</p>
          </motion.div>
        );
      })}
    </div>
  );
}

function RecommendedNext({ items }: { items: SkillGapsResponse["recommended_next"] }) {
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <h3 className="text-sm font-medium text-foreground">Recommended next</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Your highest-priority gaps for this role, ranked.
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {items.map((item, i) => {
          const meta = GAP_LEVEL_META[item.gap_level];
          return (
            <motion.li
              key={item.skill.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <Link
                href={`/skills/${item.skill.slug}`}
                className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 transition-colors duration-200 hover:bg-background"
              >
                <span className="flex items-center gap-2.5">
                  <span className="flex size-6 items-center justify-center rounded-full bg-background text-[11px] font-medium text-muted-foreground">
                    {i + 1}
                  </span>
                  <span className="text-sm text-foreground">{item.skill.name}</span>
                </span>
                <span className={cn("text-xs font-medium", meta.text)}>{meta.label}</span>
              </Link>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}

function FullBreakdown({ items }: { items: SkillGapsResponse["gaps"] }) {
  const sorted = useMemo(() => [...items].sort((a, b) => b.priority - a.priority), [items]);
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <h3 className="text-sm font-medium text-foreground">Full breakdown</h3>
      <p className="mt-1 text-xs text-muted-foreground">Every skill this role requires.</p>
      <div className="mt-4 flex flex-col divide-y divide-border">
        {sorted.map((item, i) => {
          const meta = GAP_LEVEL_META[item.gap_level];
          const barWidth = Math.max(6, Math.min(100, (item.priority / MAX_PRIORITY) * 100));
          return (
            <motion.div
              key={item.skill.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: Math.min(i * 0.03, 0.6), duration: 0.3 }}
              className="flex items-center justify-between gap-4 py-3"
            >
              <Link
                href={`/skills/${item.skill.slug}`}
                className="text-sm text-foreground transition-colors hover:text-primary"
              >
                {item.skill.name}
              </Link>
              <span className="flex items-center gap-3">
                <span className={cn("text-xs font-medium", meta.text)}>{meta.label}</span>
                <span className="h-1.5 w-24 overflow-hidden rounded-full bg-border">
                  <span
                    className={cn("block h-full rounded-full transition-all duration-700", meta.bar)}
                    style={{ width: `${barWidth}%` }}
                  />
                </span>
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
