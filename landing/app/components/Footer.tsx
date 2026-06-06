"use client";

import { motion } from "framer-motion";

export default function Footer() {
  return (
    <footer className="relative mt-12 border-t border-gold/10">
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-24 -translate-y-full bg-gradient-to-t from-background to-transparent pointer-events-none"
      />
      <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col sm:flex-row items-center justify-between gap-6">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="flex items-center gap-4"
        >
          <span
            dir="rtl"
            lang="ar"
            className="font-arabic text-3xl font-bold text-gradient-gold glow-gold-soft leading-tight"
          >
            عقاب
          </span>
          <div className="h-6 w-px bg-gold/20" />
          <span className="mono-tag text-muted">Eqaab · 2026</span>
        </motion.div>

        <p className="mono-tag text-muted-2 text-center sm:text-right">
          From Saudi Engineers to the World
        </p>
      </div>
    </footer>
  );
}
