import Image from "next/image";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";
import { cardHover, cn } from "@/lib/utils";

const quotes = [
  {
    body: "I finally understood why my resume wasn't landing interviews. The skill-gap breakdown was blunt in the right way.",
    name: "Priya Raman",
    role: "Backend Engineer",
    avatar: "https://i.pravatar.cc/150?img=32",
  },
  {
    body: "The mock interviews caught things I didn't know I was doing, like rambling past the actual answer.",
    name: "Marcus Webb",
    role: "Data Analyst",
    avatar: "https://i.pravatar.cc/150?img=68",
  },
  {
    body: "Watching my roadmap update after I finished a course felt like the tool actually knew what I'd done.",
    name: "Elena Kovac",
    role: "ML Engineer",
    avatar: "https://i.pravatar.cc/150?img=45",
  },
];

export function Testimonials() {
  return (
    <Section className="border-t border-border">
      <Container>
        <Reveal>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Early feedback from people using it.
          </h2>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {quotes.map((quote, i) => (
            <Reveal key={quote.name} delay={i * 0.08}>
              <blockquote
                className={cn(
                  cardHover,
                  "flex h-full flex-col justify-between rounded-xl border border-border bg-surface p-6"
                )}
              >
                <p className="text-sm leading-relaxed text-foreground">
                  &ldquo;{quote.body}&rdquo;
                </p>
                <footer className="mt-6 flex items-center gap-3">
                  <Image
                    src={quote.avatar}
                    alt=""
                    width={36}
                    height={36}
                    className="rounded-full"
                  />
                  <div>
                    <p className="text-sm font-medium text-foreground">{quote.name}</p>
                    <p className="text-xs text-muted-foreground">{quote.role}</p>
                  </div>
                </footer>
              </blockquote>
            </Reveal>
          ))}
        </div>
      </Container>
    </Section>
  );
}
