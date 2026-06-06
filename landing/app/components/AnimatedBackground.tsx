"use client";

import { motion } from "framer-motion";

/**
 * Abstract drone-inspired animated background.
 * Pure SVG + motion divs. No images.
 */
export default function AnimatedBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {/* Subtle grid */}
      <div className="absolute inset-0 grid-pattern opacity-60" />

      {/* Floating gold orbs */}
      <motion.div
        className="absolute -top-32 left-1/2 -translate-x-1/2 h-[520px] w-[520px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(212,175,55,0.18) 0%, rgba(212,175,55,0.04) 40%, transparent 70%)",
          filter: "blur(40px)",
        }}
        animate={{
          opacity: [0.6, 0.95, 0.6],
          scale: [1, 1.08, 1],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/2 -right-20 h-[380px] w-[380px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(212,175,55,0.10) 0%, transparent 65%)",
          filter: "blur(50px)",
        }}
        animate={{
          opacity: [0.4, 0.8, 0.4],
          x: [0, -20, 0],
        }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -bottom-20 -left-10 h-[420px] w-[420px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(212,175,55,0.08) 0%, transparent 60%)",
          filter: "blur(60px)",
        }}
        animate={{
          opacity: [0.4, 0.7, 0.4],
          y: [0, -25, 0],
        }}
        transition={{ duration: 13, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Concentric rings — drone signal motif */}
      <svg
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 opacity-25"
        width="900"
        height="900"
        viewBox="0 0 900 900"
        fill="none"
      >
        <defs>
          <radialGradient id="ringGrad" cx="50%" cy="50%" r="50%">
            <stop offset="40%" stopColor="rgba(212,175,55,0)" />
            <stop offset="100%" stopColor="rgba(212,175,55,0.55)" />
          </radialGradient>
        </defs>
        {[180, 280, 380, 460].map((r, i) => (
          <motion.circle
            key={r}
            cx="450"
            cy="450"
            r={r}
            stroke="url(#ringGrad)"
            strokeWidth="1"
            initial={{ opacity: 0.3 }}
            animate={{ opacity: [0.15, 0.6, 0.15] }}
            transition={{
              duration: 6,
              delay: i * 0.6,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
      </svg>

      {/* Particles (deterministic positions to avoid hydration mismatch) */}
      <div className="absolute inset-0">
        {PARTICLES.map((p, i) => (
          <motion.span
            key={i}
            className="absolute block rounded-full bg-gold"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              opacity: p.opacity,
              boxShadow: "0 0 12px rgba(212,175,55,0.6)",
            }}
            animate={{
              y: [0, -18, 0],
              opacity: [p.opacity * 0.4, p.opacity, p.opacity * 0.4],
            }}
            transition={{
              duration: 5 + (i % 5),
              delay: i * 0.15,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>

      {/* Top gradient fade */}
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-background to-transparent" />
      {/* Bottom gradient fade */}
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-background to-transparent" />
    </div>
  );
}

const PARTICLES = [
  { x: 12, y: 22, size: 2, opacity: 0.7 },
  { x: 28, y: 70, size: 1, opacity: 0.5 },
  { x: 44, y: 18, size: 2, opacity: 0.6 },
  { x: 58, y: 80, size: 1, opacity: 0.4 },
  { x: 72, y: 40, size: 2, opacity: 0.7 },
  { x: 84, y: 64, size: 1, opacity: 0.5 },
  { x: 90, y: 22, size: 2, opacity: 0.6 },
  { x: 18, y: 88, size: 1, opacity: 0.4 },
  { x: 38, y: 52, size: 1, opacity: 0.5 },
  { x: 66, y: 14, size: 1, opacity: 0.6 },
  { x: 8, y: 56, size: 2, opacity: 0.5 },
  { x: 96, y: 84, size: 1, opacity: 0.5 },
  { x: 50, y: 32, size: 1, opacity: 0.6 },
  { x: 24, y: 8, size: 1, opacity: 0.5 },
  { x: 78, y: 92, size: 2, opacity: 0.5 },
];
