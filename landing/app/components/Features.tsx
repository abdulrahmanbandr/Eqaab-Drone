"use client";

import { motion } from "framer-motion";
import {
  Crosshair,
  Compass,
  ShieldAlert,
  Radio,
  type LucideIcon,
} from "lucide-react";
import SectionHeading from "./SectionHeading";

interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
  index: string;
}

const FEATURES: Feature[] = [
  {
    icon: Crosshair,
    index: "F.01",
    title: "AI Object Tracking",
    description:
      "YOLOv8n + DeepSort delivers persistent, multi-class tracking with stable track IDs across frames — drones, persons, vehicles.",
  },
  {
    icon: Compass,
    index: "F.02",
    title: "Autonomous Navigation",
    description:
      "Mission waypoints, geofencing, and PX4 autopilot deliver hands-off patrols with deterministic safety failsafes.",
  },
  {
    icon: ShieldAlert,
    index: "F.03",
    title: "Drone Interception",
    description:
      "IFF classification flags hostile UAVs in real time — friendly drones authenticate; unknowns escalate to HIGH threat.",
  },
  {
    icon: Radio,
    index: "F.04",
    title: "Real-time Monitoring",
    description:
      "Structured telemetry over WebSocket — 2 Hz position updates, event-driven detections, and a live mission timeline.",
  },
];

export default function Features() {
  return (
    <section
      id="features"
      className="relative py-28 sm:py-36 px-6 max-w-7xl mx-auto"
    >
      <SectionHeading
        eyebrow="02 / Capabilities"
        title={
          <>
            Four pillars, <span className="text-gradient-gold">one</span>{" "}
            autonomous system.
          </>
        }
        description="Every capability was chosen for resilience over flash — the system stays useful when the network drops, the GPS shakes, and the operator looks away."
      />

      <div className="grid gap-6 sm:grid-cols-2">
        {FEATURES.map((feature, i) => {
          const Icon = feature.icon;
          return (
            <motion.article
              key={feature.title}
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{
                duration: 0.7,
                delay: i * 0.1,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="glass glass-hover relative overflow-hidden rounded-2xl p-8 group"
            >
              {/* Top-left index */}
              <span className="mono-tag absolute top-5 right-6 text-gold/60">
                {feature.index}
              </span>

              {/* Decorative corner lines */}
              <div
                aria-hidden
                className="absolute top-0 left-0 h-8 w-8 border-l border-t border-gold/30 rounded-tl-2xl"
              />
              <div
                aria-hidden
                className="absolute bottom-0 right-0 h-8 w-8 border-r border-b border-gold/30 rounded-br-2xl"
              />

              <div className="relative">
                <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-gold/15 to-gold/5 border border-gold/25 transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3">
                  <Icon className="h-6 w-6 text-gold" strokeWidth={2} />
                </div>
                <h3 className="font-display text-xl sm:text-2xl font-bold text-foreground mb-3">
                  {feature.title}
                </h3>
                <p className="text-muted leading-relaxed text-sm sm:text-base">
                  {feature.description}
                </p>
              </div>
            </motion.article>
          );
        })}
      </div>
    </section>
  );
}
