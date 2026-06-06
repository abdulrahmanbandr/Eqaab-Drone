"use client";

import { motion } from "framer-motion";
import { ShieldCheck, Cpu, Plane } from "lucide-react";
import SectionHeading from "./SectionHeading";

const PILLARS = [
  {
    icon: ShieldCheck,
    label: "Smart Surveillance",
    text: "Continuous, autonomous patrol of restricted zones with structured, low-bandwidth alerts — built for the field, not the lab.",
  },
  {
    icon: Cpu,
    label: "AI Tracking",
    text: "On-board YOLO inference with persistent multi-object tracking — every target keeps a track ID across frames.",
  },
  {
    icon: Plane,
    label: "Autonomous Drone",
    text: "Mission planning, geofencing, and PX4 failsafes — with hardware-level RC override always available to the pilot.",
  },
];

export default function About() {
  return (
    <section
      id="about"
      className="relative py-28 sm:py-36 px-6 max-w-7xl mx-auto"
    >
      <SectionHeading
        eyebrow="01 / About the Project"
        title={
          <>
            An <span className="text-gradient-gold">elite</span> autonomous
            drone system, engineered end-to-end.
          </>
        }
        description="Eqaab is a graduation capstone fusing autonomous flight, edge AI vision, IFF classification, and a real-time ground control station — all designed around a deliberate, metadata-only architecture for production-grade reliability."
      />

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {PILLARS.map((p, i) => {
          const Icon = p.icon;
          return (
            <motion.div
              key={p.label}
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{
                duration: 0.7,
                delay: i * 0.12,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="glass glass-hover rounded-2xl p-7 group relative overflow-hidden"
            >
              {/* Inner gold sheen on hover */}
              <div
                aria-hidden
                className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                style={{
                  background:
                    "radial-gradient(400px 200px at 0% 0%, rgba(212,175,55,0.10), transparent 60%)",
                }}
              />
              <div className="relative">
                <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gold/10 border border-gold/25">
                  <Icon className="h-5 w-5 text-gold" strokeWidth={2.2} />
                </div>
                <h3 className="font-display font-semibold text-lg text-foreground mb-2">
                  {p.label}
                </h3>
                <p className="text-muted text-sm leading-relaxed">{p.text}</p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
