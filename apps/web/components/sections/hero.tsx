"use client";

import { motion, useReducedMotion } from "motion/react";
import { ButtonLink } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { SkillNetwork } from "@/components/three/skill-network";

export function Hero() {
  const reduce = useReducedMotion();

  return (
    <section className="relative overflow-hidden pt-20 lg:pt-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 [background:var(--gradient-ambient)]"
      />

      <Container className="relative grid min-h-[calc(100dvh-5rem)] items-center gap-12 lg:grid-cols-2 lg:gap-8">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="text-4xl font-semibold tracking-tighter text-foreground sm:text-5xl lg:text-6xl">
            Turn your career into an intelligent roadmap.
          </h1>
          <p className="mt-6 max-w-[46ch] text-lg leading-relaxed text-muted-foreground">
            AI-powered career intelligence that understands your skills, identifies your gaps,
            and builds the path to your next opportunity.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <ButtonLink href="/dashboard" size="lg">
              Get started
            </ButtonLink>
            <ButtonLink href="#how-it-works" variant="secondary" size="lg">
              See how it works
            </ButtonLink>
          </div>
        </motion.div>

        <motion.div
          initial={reduce ? false : { opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="relative aspect-square w-full max-w-md justify-self-center lg:max-w-none lg:justify-self-stretch"
        >
          <SkillNetwork />
        </motion.div>
      </Container>
    </section>
  );
}
