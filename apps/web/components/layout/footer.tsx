import Link from "next/link";
import { Container } from "@/components/ui/container";

const columns = [
  {
    heading: "Product",
    links: [
      { label: "Resume analysis", href: "#product" },
      { label: "Job matching", href: "#product" },
      { label: "AI interviews", href: "#product" },
      { label: "Pricing", href: "#pricing" },
    ],
  },
  {
    heading: "Company",
    links: [
      { label: "About", href: "#" },
      { label: "Careers", href: "#" },
      { label: "Contact", href: "#" },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "Privacy", href: "#" },
      { label: "Terms", href: "#" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border">
      <Container className="grid grid-cols-2 gap-10 py-16 lg:grid-cols-5">
        <div className="col-span-2">
          <span className="text-base font-semibold tracking-tight text-foreground">
            CareerAI
          </span>
          <p className="mt-3 max-w-xs text-sm text-muted-foreground">
            AI-powered career intelligence for people who want their next role to be a better
            one.
          </p>
        </div>

        {columns.map((column) => (
          <div key={column.heading}>
            <h3 className="text-sm font-medium text-foreground">{column.heading}</h3>
            <ul className="mt-4 space-y-3">
              {column.links.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Container>

      <div className="border-t border-border py-6">
        <Container>
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} CareerAI. All rights reserved.
          </p>
        </Container>
      </div>
    </footer>
  );
}
