import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { ButtonLink } from "@/components/ui/button";
import { Reveal } from "@/components/motion/reveal";

export function Cta() {
  return (
    <Section className="border-t border-border bg-surface">
      <Container className="flex flex-col items-center text-center">
        <Reveal>
          <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Your next role starts with knowing where you actually stand.
          </h2>
          <p className="mx-auto mt-4 max-w-[42ch] text-base text-muted-foreground">
            Upload a resume and get a real analysis in minutes, not a generic checklist.
          </p>
          <div className="mt-8">
            <ButtonLink href="/sign-up" size="lg">
              Get started
            </ButtonLink>
          </div>
        </Reveal>
      </Container>
    </Section>
  );
}
