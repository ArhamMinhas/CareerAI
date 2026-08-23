import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { MotionProvider } from "@/components/layout/motion-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "CareerAI — AI Career Intelligence Platform",
    template: "%s | CareerAI",
  },
  description:
    "AI-powered career intelligence: resume scoring, skill-gap analysis, job matching, and personalized career roadmaps.",
  robots: { index: true, follow: true },
  openGraph: {
    title: "CareerAI — AI Career Intelligence Platform",
    description:
      "AI-powered career intelligence: resume scoring, skill-gap analysis, job matching, and personalized career roadmaps.",
    url: siteUrl,
    siteName: "CareerAI",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CareerAI — AI Career Intelligence Platform",
    description:
      "AI-powered career intelligence: resume scoring, skill-gap analysis, job matching, and personalized career roadmaps.",
  },
};

function OrganizationJsonLd() {
  // Site-wide brand identity (docs/SEO.md §2.4) — every page gets this once, from here,
  // rather than each page re-declaring it (the landing page used to; now it only adds what's
  // specific to it).
  const data = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "CareerAI",
    url: siteUrl,
  };
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <OrganizationJsonLd />
        <ThemeProvider>
          <MotionProvider>{children}</MotionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
