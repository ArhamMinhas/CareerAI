import { Upload, Sparkles, TrendingUp } from "lucide-react";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";

const steps = [
  {
    icon: Upload,
    title: "Upload your resume",
    body: "PDF or DOCX. We parse it with a mix of NLP and structured extraction, not a single opaque prompt.",
  },
  {
    icon: Sparkles,
    title: "Get your analysis",
    body: "A scored breakdown of your skills, experience, and gaps against the role you're targeting.",
  },
  {
    icon: TrendingUp,
    title: "Follow your roadmap",
    body: "A sequenced plan of skills, projects, and practice interviews to close the gap.",
  },
];

export function HowItWorks() {
  return (
    <Section id="how-it-works" className="border-t border-border">
      <Container>
        <Reveal>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            From resume to roadmap in three steps.
          </h2>
        </Reveal>

        <div className="mt-16 grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-8">
          {steps.map((step, i) => (
            <Reveal key={step.title} delay={i * 0.08} className="group">
              <step.icon
                className="size-6 text-primary transition-transform duration-200 ease-out group-hover:scale-110"
                strokeWidth={1.5}
              />
              <h3 className="mt-5 text-lg font-medium text-foreground">{step.title}</h3>
              <p className="mt-2 max-w-[32ch] text-sm leading-relaxed text-muted-foreground">
                {step.body}
              </p>
            </Reveal>
          ))}
        </div>
      </Container>
    </Section>
  );
}
