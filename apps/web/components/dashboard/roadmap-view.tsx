"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, Loader2, Map, RefreshCw, Sparkles, Trash2 } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { CareerGoal } from "@/lib/types/profile";
import type { CareerPath } from "@/lib/types/career-path";
import type {
  LearningPathItem,
  LearningRoadmap,
  RoadmapPhase,
} from "@/lib/types/learning-roadmap";

const PHASE_META: Record<RoadmapPhase, { label: string; description: string }> = {
  foundations: { label: "Foundations", description: "Start here — the building blocks." },
  core: { label: "Core skills", description: "Build on the foundations above." },
  advanced: { label: "Advanced & polish", description: "Round things out." },
};

const PHASE_ORDER: RoadmapPhase[] = ["foundations", "core", "advanced"];

type RoadmapResult =
  | { targetRole: string; kind: "not-generated" }
  | { targetRole: string; kind: "loaded"; data: LearningRoadmap }
  | { targetRole: string; kind: "error"; message: string };

type GenerateState =
  | { kind: "idle" }
  | { kind: "generating" }
  | { kind: "rate_limited"; retryAfterSeconds: number | null }
  | { kind: "error"; message: string };

export function RoadmapView() {
  const [careerPaths, setCareerPaths] = useState<CareerPath[] | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [roadmapResult, setRoadmapResult] = useState<RoadmapResult | null>(null);
  const [generateState, setGenerateState] = useState<GenerateState>({ kind: "idle" });
  const [pendingItemIds, setPendingItemIds] = useState<Set<string>>(new Set());

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

  useEffect(() => {
    if (!targetRole) return;
    let active = true;
    setGenerateState({ kind: "idle" });
    apiFetch<LearningRoadmap>(
      `/api/v1/learning-roadmap?target_role=${encodeURIComponent(targetRole)}`
    )
      .then((data) => {
        if (active) setRoadmapResult({ targetRole, kind: "loaded", data });
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setRoadmapResult({ targetRole, kind: "not-generated" });
        } else {
          const message = err instanceof ApiError ? err.message : "Couldn't load your roadmap.";
          setRoadmapResult({ targetRole, kind: "error", message });
        }
      });
    return () => {
      active = false;
    };
  }, [targetRole]);

  async function handleGenerate() {
    if (!targetRole || generateState.kind === "generating") return;
    setGenerateState({ kind: "generating" });
    try {
      const data = await apiFetch<LearningRoadmap>(
        `/api/v1/learning-roadmap/generate?target_role=${encodeURIComponent(targetRole)}`,
        { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() } }
      );
      setRoadmapResult({ targetRole, kind: "loaded", data });
      setGenerateState({ kind: "idle" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setGenerateState({ kind: "rate_limited", retryAfterSeconds: err.retryAfterSeconds });
      } else {
        const message = err instanceof ApiError ? err.message : "Couldn't generate a roadmap.";
        setGenerateState({ kind: "error", message });
      }
    }
  }

  async function handleToggleItem(item: LearningPathItem) {
    setPendingItemIds((prev) => new Set(prev).add(item.id));
    try {
      const data = await apiFetch<LearningRoadmap>(`/api/v1/learning-roadmap/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: !item.completed }),
      });
      setRoadmapResult({ targetRole, kind: "loaded", data });
    } catch {
      // Leave the checkbox as-is; the user can retry the click.
    } finally {
      setPendingItemIds((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    }
  }

  async function handleDelete() {
    if (!targetRole) return;
    try {
      await apiFetch(`/api/v1/learning-roadmap?target_role=${encodeURIComponent(targetRole)}`, {
        method: "DELETE",
      });
      setRoadmapResult({ targetRole, kind: "not-generated" });
    } catch {
      // Best-effort; leave the roadmap showing if the delete failed.
    }
  }

  const isLoadingCatalog = careerPaths === null;
  const isLoadingRoadmap = targetRole !== "" && roadmapResult?.targetRole !== targetRole;
  const currentResult = roadmapResult?.targetRole === targetRole ? roadmapResult : null;

  return (
    <div className="flex flex-col gap-6">
      <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-foreground">Target role</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Pick a curated career path to build a roadmap toward.
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
              <>
                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={generateState.kind === "generating"}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border-strong px-3 text-xs font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-background disabled:opacity-50"
                >
                  <RefreshCw
                    className={cn("size-3.5", generateState.kind === "generating" && "animate-spin")}
                    strokeWidth={1.75}
                  />
                  Regenerate
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-muted-foreground transition-colors duration-200 hover:text-danger"
                  aria-label="Start over"
                >
                  <Trash2 className="size-3.5" strokeWidth={1.75} />
                </button>
              </>
            ) : null}
          </div>
        </div>
        {generateState.kind === "rate_limited" ? (
          <p className="mt-3 text-xs text-warning">
            You&apos;ve generated a lot of roadmaps in a short window —{" "}
            {generateState.retryAfterSeconds !== null
              ? `try again in about ${generateState.retryAfterSeconds}s.`
              : "please slow down and try again shortly."}
          </p>
        ) : generateState.kind === "error" ? (
          <p className="mt-3 text-xs text-danger">{generateState.message}</p>
        ) : null}
      </div>

      <AnimatePresence mode="wait">
        {isLoadingCatalog || isLoadingRoadmap ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-48 animate-pulse rounded-xl border border-border bg-surface"
          />
        ) : !targetRole ? (
          <EmptyState
            key="no-target"
            title="Pick a target role above"
            description="We'll sequence a step-by-step roadmap from your skill gaps for that role."
          />
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
        ) : currentResult?.kind === "not-generated" ? (
          <motion.div
            key="not-generated"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={cn(
              cardHover,
              "flex flex-col items-center gap-3 rounded-xl border border-border bg-surface px-6 py-16 text-center"
            )}
          >
            <Map className="size-6 text-muted-foreground" strokeWidth={1.5} />
            <p className="max-w-[42ch] text-sm text-muted-foreground">
              No roadmap yet for this role. We&apos;ll sequence your skill gaps into ordered
              steps, with curated resources where we have them.
            </p>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={generateState.kind === "generating"}
              className="mt-1 inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all duration-200 hover:opacity-90 disabled:opacity-50"
            >
              {generateState.kind === "generating" ? (
                <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
              ) : null}
              Generate my roadmap
            </button>
          </motion.div>
        ) : currentResult?.kind === "loaded" ? (
          <motion.div
            key="loaded"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex flex-col gap-6"
          >
            <RoadmapSummary roadmap={currentResult.data} />
            {currentResult.data.items.length === 0 ? (
              <EmptyState
                title="You're all set"
                description="No gaps to sequence for this role right now — nice work."
              />
            ) : (
              PHASE_ORDER.map((phase) => {
                const items = currentResult.data.items.filter((item) => item.phase === phase);
                if (items.length === 0) return null;
                return (
                  <PhaseSection
                    key={phase}
                    phase={phase}
                    items={items}
                    pendingItemIds={pendingItemIds}
                    onToggle={handleToggleItem}
                  />
                );
              })
            )}
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

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={cn(
        cardHover,
        "flex flex-col items-center gap-2 rounded-xl border border-border bg-surface px-6 py-14 text-center"
      )}
    >
      <Sparkles className="size-6 text-muted-foreground" strokeWidth={1.5} />
      <h3 className="mt-2 text-sm font-medium text-foreground">{title}</h3>
      <p className="max-w-[40ch] text-sm text-muted-foreground">{description}</p>
    </motion.div>
  );
}

function RoadmapSummary({ roadmap }: { roadmap: LearningRoadmap }) {
  const percent =
    roadmap.progress.total === 0
      ? 0
      : Math.round((roadmap.progress.completed / roadmap.progress.total) * 100);
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          {roadmap.career_path.title}
        </h2>
        <span className="text-sm font-medium text-muted-foreground">
          {roadmap.progress.completed}/{roadmap.progress.total} done
        </span>
      </div>
      {roadmap.overview ? (
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{roadmap.overview}</p>
      ) : null}
      <span className="mt-4 block h-1.5 w-full overflow-hidden rounded-full bg-border">
        <span
          className="block h-full rounded-full bg-primary transition-all duration-700"
          style={{ width: `${percent}%` }}
        />
      </span>
    </div>
  );
}

function PhaseSection({
  phase,
  items,
  pendingItemIds,
  onToggle,
}: {
  phase: RoadmapPhase;
  items: LearningPathItem[];
  pendingItemIds: Set<string>;
  onToggle: (item: LearningPathItem) => void;
}) {
  const meta = PHASE_META[phase];
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <h3 className="text-sm font-medium text-foreground">{meta.label}</h3>
      <p className="mt-1 text-xs text-muted-foreground">{meta.description}</p>
      <div className="mt-4 flex flex-col divide-y divide-border">
        {items.map((item) => (
          <RoadmapItemRow
            key={item.id}
            item={item}
            pending={pendingItemIds.has(item.id)}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  );
}

function RoadmapItemRow({
  item,
  pending,
  onToggle,
}: {
  item: LearningPathItem;
  pending: boolean;
  onToggle: (item: LearningPathItem) => void;
}) {
  return (
    <div className="flex flex-col gap-2.5 py-3.5">
      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={item.completed}
          disabled={pending}
          onChange={() => onToggle(item)}
          className="mt-0.5 size-4 shrink-0 rounded border-border-strong accent-primary disabled:opacity-50"
        />
        <Link
          href={`/skills/${item.skill.slug}`}
          className={cn(
            "text-sm text-foreground transition-colors hover:text-primary",
            item.completed && "text-muted-foreground line-through"
          )}
        >
          {item.skill.name}
        </Link>
      </label>
      {item.resources.length > 0 ? (
        <ul className="ml-7 flex flex-wrap gap-2">
          {item.resources.map((resource) => (
            <li key={resource.id}>
              {resource.url ? (
                <a
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-border-strong px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                >
                  {resource.title}
                </a>
              ) : resource.resource_slug ? (
                <Link
                  href={`/resources/${resource.resource_slug}`}
                  className="rounded-full border border-border-strong px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                >
                  {resource.title}
                </Link>
              ) : (
                <span className="rounded-full border border-dashed border-border-strong px-2.5 py-1 text-xs text-muted-foreground">
                  {resource.title}
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="ml-7 text-xs text-muted-foreground/70">No curated resources yet.</p>
      )}
    </div>
  );
}
