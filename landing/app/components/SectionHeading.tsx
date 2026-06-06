"use client";

import { motion } from "framer-motion";

interface SectionHeadingProps {
  eyebrow: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  align?: "center" | "left";
}

export default function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
}: SectionHeadingProps) {
  const alignment = align === "center" ? "items-center text-center" : "items-start text-left";
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={`flex flex-col gap-4 ${alignment} mb-14`}
    >
      <span className="mono-tag text-gold/80">{eyebrow}</span>
      <h2 className="font-display font-bold text-3xl sm:text-4xl md:text-5xl tracking-tight max-w-3xl">
        {title}
      </h2>
      {description && (
        <p className="text-muted max-w-2xl leading-relaxed">{description}</p>
      )}
      <div className="mt-2 h-px w-24 divider-gold" />
    </motion.div>
  );
}
