import type { Metadata } from "next";
import { ProfilePageClient } from "@/components/profile/profile-page-client";

export const metadata: Metadata = {
  title: "Profile",
  robots: { index: false, follow: false },
};

export default function ProfilePage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Profile</h1>
        <p className="text-sm text-muted-foreground">
          Education, experience, projects, skills, and career goals — used to power your
          resume analysis and job matches once those ship.
        </p>
      </div>

      <div className="mt-8 max-w-3xl">
        <ProfilePageClient />
      </div>
    </div>
  );
}
