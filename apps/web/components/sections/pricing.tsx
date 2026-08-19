import { Check } from "lucide-react";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { ButtonLink } from "@/components/ui/button";
import { Reveal } from "@/components/motion/reveal";
import { cn } from "@/lib/utils";

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    features: ["1 resume analysis", "Basic skill-gap report", "5 job matches per month"],
    cta: "Get started",
    href: "/dashboard",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$19",
    period: "per month",
    features: [
      "Unlimited resume analyses",
      "Full skill-gap and roadmap",
      "Unlimited job matching",
      "AI mock interviews",
    ],
    cta: "Get started",
    href: "/dashboard",
    highlighted: true,
  },
  {
    name: "Team",
    price: "Custom",
    period: "for career centers and bootcamps",
    features: ["Everything in Pro", "Cohort analytics", "Dedicated onboarding"],
    cta: "Contact us",
    href: "#",
    highlighted: false,
  },
];

export function Pricing() {
  return (
    <Section id="pricing" className="border-t border-border">
      <Container>
        <Reveal>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Simple pricing, upgrade when you need to.
          </h2>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-3">
          {tiers.map((tier, i) => (
            <Reveal
              key={tier.name}
              delay={i * 0.08}
              className={cn(
                "flex flex-col rounded-xl border p-8",
                tier.highlighted
                  ? "border-primary bg-surface shadow-lg"
                  : "border-border bg-background"
              )}
            >
              <h3 className="text-sm font-medium text-foreground">{tier.name}</h3>
              <div className="mt-4 flex items-baseline gap-1.5">
                <span className="text-4xl font-semibold tracking-tight text-foreground">
                  {tier.price}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{tier.period}</p>

              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm text-foreground">
                    <Check className="mt-0.5 size-4 shrink-0 text-primary" strokeWidth={2} />
                    {feature}
                  </li>
                ))}
              </ul>

              <ButtonLink
                href={tier.href}
                variant={tier.highlighted ? "primary" : "secondary"}
                className="mt-8 w-full"
              >
                {tier.cta}
              </ButtonLink>
            </Reveal>
          ))}
        </div>
      </Container>
    </Section>
  );
}
