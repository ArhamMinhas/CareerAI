"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Search } from "lucide-react";

export function JobSearchInput() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [value, setValue] = useState(searchParams.get("q") ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function navigate(nextValue: string) {
    const params = new URLSearchParams(searchParams);
    if (nextValue.trim()) {
      params.set("q", nextValue.trim());
    } else {
      params.delete("q");
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => navigate(value), 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // Only re-runs the debounce timer when the input value itself changes — including
    // `router`/`pathname`/`searchParams` would re-fire this effect on every navigation this
    // same input just caused, fighting its own debounce.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    // A plain <input> outside a <form> never responds to Enter at all — without this, pressing
    // Enter does nothing and the user has to sit through the 400ms debounce (or it looks broken
    // if they navigate away before it fires). Cancel the pending debounce and search immediately.
    if (e.key !== "Enter") return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    navigate(value);
  }

  return (
    <div className="relative w-full max-w-md">
      <Search
        className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        strokeWidth={1.75}
      />
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search job titles, companies, keywords…"
        className="h-11 w-full rounded-lg border border-border-strong bg-background pl-10 pr-4 text-sm text-foreground outline-none transition-colors duration-200 placeholder:text-muted-foreground hover:border-primary/40 focus:border-primary/60"
      />
    </div>
  );
}
