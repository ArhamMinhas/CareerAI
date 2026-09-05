"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { apiFetch, apiFetchWithMeta, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/input";
import { cardHover, cn } from "@/lib/utils";
import type { AdminUser, Role } from "@/lib/types/admin";

const ROLES: Role[] = ["USER", "ADMIN", "RECRUITER"];

export function AdminUsersView() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [q, setQ] = useState("");
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [myId, setMyId] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<AdminUser>("/api/v1/auth/me")
      .then((me) => setMyId(me.id))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ limit: "20" });
    if (q.trim()) params.set("q", q.trim());
    apiFetchWithMeta<AdminUser[]>(`/api/v1/admin/users?${params.toString()}`)
      .then((result) => {
        if (!active) return;
        setUsers(result.data);
        setNextCursor(result.meta.next_cursor);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof ApiError ? err.message : "Couldn't load users.");
      });
    return () => {
      active = false;
    };
  }, [q]);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const params = new URLSearchParams({ limit: "20", cursor: nextCursor });
      if (q.trim()) params.set("q", q.trim());
      const result = await apiFetchWithMeta<AdminUser[]>(
        `/api/v1/admin/users?${params.toString()}`
      );
      setUsers((prev) => [...(prev ?? []), ...result.data]);
      setNextCursor(result.meta.next_cursor);
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleRoleChange(user: AdminUser, role: Role) {
    setPendingIds((prev) => new Set(prev).add(user.id));
    setError(null);
    try {
      const updated = await apiFetch<AdminUser>(`/api/v1/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      setUsers((prev) => (prev ?? []).map((u) => (u.id === user.id ? updated : u)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update this user's role.");
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(user.id);
        return next;
      });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search by email…"
        className="max-w-80"
      />
      {error ? <p className="text-xs text-danger">{error}</p> : null}

      {users === null ? (
        <div className="h-64 animate-pulse rounded-xl border border-border bg-surface" />
      ) : (
        <div className={cn(cardHover, "overflow-x-auto rounded-xl border border-border bg-surface")}>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Verified</th>
                <th className="px-4 py-3 font-medium">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-2.5 text-foreground">{user.email}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <Select
                        value={user.role}
                        disabled={pendingIds.has(user.id) || user.id === myId}
                        onChange={(e) => handleRoleChange(user, e.target.value as Role)}
                        className="h-8 w-32 text-xs"
                      >
                        {ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </Select>
                      {pendingIds.has(user.id) ? (
                        <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {user.email_verified ? "Yes" : "No"}
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {nextCursor ? (
        <button
          type="button"
          onClick={loadMore}
          disabled={loadingMore}
          className="mx-auto inline-flex h-10 items-center gap-2 rounded-lg border border-border-strong px-5 text-sm font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-surface disabled:opacity-50"
        >
          {loadingMore ? <Loader2 className="size-4 animate-spin" strokeWidth={1.75} /> : null}
          Load more
        </button>
      ) : null}
    </div>
  );
}
