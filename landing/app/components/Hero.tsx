"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { ArrowDown } from "lucide-react";
import AnimatedBackground from "./AnimatedBackground";

export default function Hero() {
  // Try the user's PNG first; gracefully fall back to the bundled SVG mark.
  const [logoSrc, setLogoSrc] = useState("/logo.png");

  return (
    <section
      id="hero"
      className="relative min-h-screen w-full flex items-center justify-center overflow-hidden"
    >
      <AnimatedBackground />

      {/* Hero content */}
      <div className="relative z-10 mx-auto max-w-5xl px-6 text-center">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="mb-8 flex justify-center"
        >
          <div className="relative">
            <div
              aria-hidden
              className="absolute inset-0 rounded-full blur-2xl bg-gold/30 animate-pulse-glow"
            />
            {/* Drop your final logo at /public/logo.png to override the SVG fallback */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={logoSrc}
              alt="Eqaab Logo"
              width={120}
              height={120}
              onError={() => setLogoSrc("/logo.svg")}
              className="relative h-24 w-24 sm:h-28 sm:w-28 object-contain"
            />
          </div>
        </motion.div>

        {/* Eyebrow line */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mono-tag text-gold/80 mb-6"
        >
          From Saudi Engineers to the World
        </motion.p>

        {/* Arabic title */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
          dir="rtl"
          lang="ar"
          // For Arabic in Thmanyah Serif Display:
          //  - font-bold (700) instead of font-black (900) — Black renders the
          //    dot of ب as a stylized wedge; Bold gives a clean conventional dot.
          //  - normal letter-spacing (negative tracking breaks Arabic shaping).
          //  - generous line-height + padding-bottom so the descender dot has room.
          className="font-arabic font-bold text-7xl sm:text-8xl md:text-9xl leading-[1.2] pb-3 mb-4 text-gradient-gold glow-gold"
        >
          عــــــــقــــــــاب
        </motion.h1>

        {/* Divider */}
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ duration: 0.9, delay: 0.7 }}
          className="mx-auto mb-8 h-px w-32 divider-gold origin-center"
        />

        {/* English title */}
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.85 }}
          className="font-display font-bold text-2xl sm:text-3xl md:text-4xl text-foreground/90 max-w-3xl mx-auto leading-tight"
        >
          Autonomous AI-Powered Object Tracking{" "}
          <span className="text-gradient-gold-soft">Drone</span>{" "}
          for Smart Surveillance
        </motion.h2>

        {/* Sub-tagline */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.1 }}
          className="mt-6 text-muted text-base sm:text-lg max-w-xl mx-auto"
        >
          Edge AI · Real-time tracking · Identification Friend or Foe (IFF) ·
          Built for the field.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.3 }}
          className="mt-10 flex flex-col sm:flex-row gap-3 justify-center items-center"
        >
          <a
            href="#about"
            className="group relative inline-flex items-center gap-2 rounded-full bg-gold px-7 py-3 text-sm font-semibold text-background transition-all hover:shadow-[0_0_30px_-5px_rgba(212,175,55,0.6)] hover:scale-[1.02]"
          >
            Explore the System
            <ArrowDown className="h-4 w-4 transition-transform group-hover:translate-y-0.5" />
          </a>
          <a
            href="#team"
            className="inline-flex items-center gap-2 rounded-full border border-gold/30 px-7 py-3 text-sm font-semibold text-foreground/90 backdrop-blur-sm transition-all hover:border-gold/70 hover:text-gold"
          >
            Meet the Team
          </a>
        </motion.div>
      </div>

    </section>
  );
}
