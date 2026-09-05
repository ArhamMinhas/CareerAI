"use client";

import { useEffect, useState } from "react";
import { Activity, Cpu, Database } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { AIUsage, ModelMetrics, SystemHealth } from "@/lib/types/admin";

type LoadState =
  | { kind: "loading" }
  | { kind: "loaded"; health: SystemHealth; usage: AIUsage; metrics: ModelMetrics }
  | { kind: "error"; message: string };

export function AdminOverviewView() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<SystemHealth>("/api/v1/admin/system-health"),
      apiFetch<AIUsage>("/api/v1/admin/ai-usage"),
      apiFetch<ModelMetrics>("/api/v1/admin/model-metrics"),
    ])
      .then(([health, usage, metrics]) => {
        if (active) setState({ kind: "loaded", health, usage, metrics });
      })
      .catch((err) => {
        if (!active) return;
        const message = err instanceof ApiError ? err.message : "Couldn't load admin overview.";
        setState({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return <div className="h-64 animate-pulse rounded-xl border border-border bg-surface" />;
  }

  if (state.kind === "error") {
    return (
      <div className="rounded-xl border border-danger/30 bg-surface p-6 text-center">
        <p className="text-sm text-danger">{state.message}</p>
      </div>
    );
  }

  const { health, usage, metrics } = state;

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-4">
        <h2 className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Activity className="size-4 text-muted-foreground" strokeWidth={1.75} />
          System health
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatusCard label="Database" ok={health.database_ok} />
          <StatusCard label="Redis" ok={health.redis_ok} />
          <NumberCard label="Users" value={health.total_users} />
          <NumberCard label="Jobs" value={health.total_jobs} />
          <NumberCard label="Resumes" value={health.total_resumes} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Cpu className="size-4 text-muted-foreground" strokeWidth={1.75} />
          AI usage, by feature
        </h2>
        {usage.by_feature.length === 0 ? (
          <p className="text-xs text-muted-foreground">No AI calls logged yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Feature</th>
                  <th className="px-4 py-3 font-medium">Calls</th>
                  <th className="px-4 py-3 font-medium">Prompt tokens</th>
                  <th className="px-4 py-3 font-medium">Completion tokens</th>
                  <th className="px-4 py-3 font-medium">Avg latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {usage.by_feature.map((row) => (
                  <tr key={row.feature}>
                    <td className="px-4 py-2.5 text-foreground">{row.feature}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{row.call_count}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">
                      {row.prompt_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">
                      {row.completion_tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">
                      {Math.round(row.avg_latency_ms)}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Database className="size-4 text-muted-foreground" strokeWidth={1.75} />
          Trained model metrics
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metrics.models.map((model) => (
            <div
              key={model.name}
              className={cn(cardHover, "rounded-xl border border-border bg-surface p-5")}
            >
              <p className="text-sm font-medium text-foreground">{model.name}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">v{model.version}</p>
              {model.available ? (
                <>
                  <p className="mt-3 text-xl font-semibold tracking-tight text-foreground">
                    {model.score !== null ? model.score.toFixed(3) : "—"}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">
                      {model.metric}
                    </span>
                  </p>
                  {model.retrained_at ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Retrained {new Date(model.retrained_at).toLocaleDateString()}
                    </p>
                  ) : null}
                </>
              ) : (
                <p className="mt-3 text-xs text-warning">Metrics unavailable</p>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatusCard({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-5")}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-2 text-sm font-semibold",
          ok ? "text-success" : "text-danger"
        )}
      >
        {ok ? "Healthy" : "Down"}
      </p>
    </div>
  );
}

function NumberCard({ label, value }: { label: string; value: number }) {
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-5")}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-xl font-semibold tracking-tight text-foreground">
        {value.toLocaleString()}
      </p>
    </div>
  );
}
