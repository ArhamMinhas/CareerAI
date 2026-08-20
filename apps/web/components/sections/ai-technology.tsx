import { FileText, Cpu, Database, Sparkles, Target, ArrowRight } from "lucide-react";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";

const stages = [
  { icon: FileText, label: "Parse" },
  { icon: Cpu, label: "Extract" },
  { icon: Database, label: "Embed & retrieve" },
  { icon: Sparkles, label: "Reason" },
  { icon: Target, label: "Recommend" },
];

export function AiTechnology() {
  return (
    <Section className="border-t border-border">
      <Container>
        <Reveal className="max-w-xl">
          <h2 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Real AI engineering, not a single prompt.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Scoring and ranking run on deterministic rules and small ML models. The LLM is
            reserved for what it&apos;s actually good at: reading, extracting, and explaining.
          </p>
        </Reveal>

        <Reveal delay={0.1} className="mt-16 overflow-x-auto">
          <div className="flex min-w-max items-center gap-3">
            {stages.map((stage, i) => (
              <div key={stage.label} className="flex items-center gap-3">
                <div className="group flex flex-col items-center gap-3 rounded-xl border border-border bg-surface px-6 py-5 transition-all duration-200 ease-out hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5">
                  <stage.icon className="size-5 text-primary transition-transform duration-200 group-hover:scale-110" strokeWidth={1.5} />
                  <span className="text-xs font-medium text-foreground">{stage.label}</span>
                </div>
                {i < stages.length - 1 ? (
                  <ArrowRight
                    className="size-4 shrink-0 text-muted-foreground"
                    strokeWidth={1.5}
                  />
                ) : null}
              </div>
            ))}
          </div>
        </Reveal>
      </Container>
    </Section>
  );
}
