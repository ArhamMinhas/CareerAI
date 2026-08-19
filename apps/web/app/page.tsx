import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Hero } from "@/components/sections/hero";
import { ProductTour } from "@/components/sections/product-tour";
import { HowItWorks } from "@/components/sections/how-it-works";
import { MarketIntelligence } from "@/components/sections/market-intelligence";
import { AiTechnology } from "@/components/sections/ai-technology";
import { Testimonials } from "@/components/sections/testimonials";
import { Pricing } from "@/components/sections/pricing";
import { Faq } from "@/components/sections/faq";
import { Cta } from "@/components/sections/cta";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

const faqs = [
  {
    question: "How is my resume actually scored?",
    answer:
      "A weighted formula across ATS compatibility, skills, experience, projects, education, achievements, keywords, and structure, with a plain-language explanation for every sub-score.",
  },
  {
    question: "Does an AI model make every decision?",
    answer:
      "No. Scoring, ranking, and skill-gap comparisons run on deterministic rules and small trained models. The LLM handles extraction, summarization, and explaining results.",
  },
  {
    question: "What happens to my resume data?",
    answer:
      "Your file is stored privately and only accessible to your account, used to power your own analysis and recommendations.",
  },
  {
    question: "Can I use this without a specific target role?",
    answer:
      "Yes. Start with a general skills and resume audit, then narrow to a specific role once you know what you're aiming for.",
  },
];

function JsonLd() {
  const data = [
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "CareerAI",
      url: siteUrl,
    },
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: "CareerAI",
      url: siteUrl,
    },
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqs.map((faq) => ({
        "@type": "Question",
        name: faq.question,
        acceptedAnswer: { "@type": "Answer", text: faq.answer },
      })),
    },
  ];

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export default function Home() {
  return (
    <SmoothScroll>
      <JsonLd />
      <Navbar />
      <main>
        <Hero />
        <ProductTour />
        <HowItWorks />
        <MarketIntelligence />
        <AiTechnology />
        <Testimonials />
        <Pricing />
        <Faq />
        <Cta />
      </main>
      <Footer />
    </SmoothScroll>
  );
}
