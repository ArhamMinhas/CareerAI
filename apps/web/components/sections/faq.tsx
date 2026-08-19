import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

const faqs = [
  {
    question: "How is my resume actually scored?",
    answer:
      "A weighted formula across ATS compatibility, skills, experience, projects, education, achievements, keywords, and structure. Every sub-score comes with a plain-language explanation, and the weights are configurable rather than hidden inside a prompt.",
  },
  {
    question: "Does an AI model make every decision?",
    answer:
      "No. Scoring, ranking, and skill-gap comparisons run on deterministic rules and small trained models. The LLM handles extraction, summarization, and explaining results in natural language, never the underlying math.",
  },
  {
    question: "What happens to my resume data?",
    answer:
      "Your file is stored privately and only accessible to your account. Parsed content is used to power your own analysis and recommendations, not shared or used to train external models.",
  },
  {
    question: "Can I use this without a specific target role?",
    answer:
      "Yes. You can start with a general skills and resume audit, then narrow to a specific role once you know what you're aiming for.",
  },
];

export function Faq() {
  return (
    <Section id="faq" className="border-t border-border">
      <Container className="max-w-3xl">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Questions people ask before signing up.
          </h2>
        </Reveal>

        <Reveal delay={0.1} className="mt-12">
          <Accordion type="single" collapsible>
            {faqs.map((faq) => (
              <AccordionItem key={faq.question} value={faq.question}>
                <AccordionTrigger>{faq.question}</AccordionTrigger>
                <AccordionContent>{faq.answer}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </Reveal>
      </Container>
    </Section>
  );
}
