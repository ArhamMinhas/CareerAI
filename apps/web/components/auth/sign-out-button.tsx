"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

export function SignOutButton({ className }: { className?: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSignOut() {
    setLoading(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={handleSignOut}
      disabled={loading}
      className={cn(
        "flex items-center gap-2 rounded-lg text-sm text-muted-foreground transition-colors duration-200 hover:text-foreground disabled:opacity-50",
        className
      )}
    >
      <LogOut className="size-4" strokeWidth={1.75} />
      Sign out
    </button>
  );
}
