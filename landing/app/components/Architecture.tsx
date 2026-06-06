"use client";

import { motion } from "framer-motion";
import {
  Plane,
  BrainCircuit,
  Cloud,
  LayoutDashboard,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import SectionHeading from "./SectionHeading";

interface FlowNode {
  icon: LucideIcon;
  label: string;
  caption: string;
}

const NODES: FlowNode[] = [
  { icon: Plane, label: "Drone", caption: "Pi 5 + Pixhawk · Edge" },
  { icon: BrainCircuit, label: "AI Model", caption: "YOLO + DeepSort + IFF" },
  { icon: Cloud, label: "Cloud", caption: "FastAPI · WebSocket Gateway" },
  { icon: LayoutDashboard, label: "Dashboard", caption: "React GCS · Live Map" },
];

export default function Architecture() {
  return (
    <section
      id="architecture"
      className="relative py-28 sm:py-36 px-6 max-w-7xl mx-auto"
    >
      <SectionHeading
        eyebrow="03 / System Architecture"
        title={
          <>
            From sensor edge to{" "}
            <span className="text-gradient-gold">operator screen</span>.
          </>
        }
        description="A three-tier pipeline: detect at the edge, process in the cloud, decide at the dashboard. Structured JSON the whole way — no video streams, no surprises."
      />

      <div className="relative">
        {/* Glow plate behind the flow */}
        <div
          aria-hidden
          className="absolute inset-0 -z-10 dot-pattern opacity-40"
        />

        {/* Flow */}
        <div className="relative grid gap-6 lg:gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] lg:items-stretch">
          {NODES.map((node, i) => (
            <FlowFragment
              key={node.label}
              node={node}
              index={i}
              isLast={i === NODES.length - 1}
            />
          ))}
        </div>

        {/* Stats strip */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mt-16 grid gap-4 sm:grid-cols-3"
        >
          {[
            { value: "~ 5 KB/s", label: "Avg. uplink (metadata only)" },
            { value: "8–12 FPS", label: "On-device inference" },
            { value: "< 200 ms", label: "Edge → operator latency" },
          ].map((s) => (
            <div
              key={s.label}
              className="glass rounded-xl p-5 text-center sm:text-left"
            >
              <div className="font-display text-2xl font-bold text-gradient-gold">
                {s.value}
              </div>
              <div className="mono-tag mt-1 text-muted">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function FlowFragment({
  node,
  index,
  isLast,
}: {
  node: FlowNode;
  index: number;
  isLast: boolean;
}) {
  const Icon = node.icon;
  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 32, scale: 0.95 }}
        whileInView={{ opacity: 1, y: 0, scale: 1 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{
          duration: 0.7,
          delay: index * 0.18,
          ease: [0.22, 1, 0.36, 1],
        }}
        className="glass glass-hover relative flex flex-col items-center justify-center text-center rounded-2xl p-7 lg:p-6 min-h-[170px]"
      >
        {/* Halo */}
        <div
          aria-hidden
          className="absolute inset-0 rounded-2xl"
          style={{
            background:
              "radial-gradient(circle at 50% 30%, rgba(212,175,55,0.08), transparent 60%)",
          }}
        />
        <div className="relative">
          <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gold/10 border border-gold/30">
            <Icon className="h-6 w-6 text-gold" strokeWidth={2} />
          </div>
          <div className="font-display font-bold text-lg text-foreground">
            {node.label}
          </div>
          <div className="mono-tag mt-1 text-muted">{node.caption}</div>
        </div>
      </motion.div>
      {!isLast && (
        <motion.div
          initial={{ opacity: 0, scale: 0.6 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, delay: index * 0.18 + 0.25 }}
          className="flex items-center justify-center text-gold/50 lg:rotate-0 rotate-90"
          aria-hidden
        >
          <ChevronRight className="h-5 w-5 animate-pulse-glow" />
        </motion.div>
      )}
    </>
  );
}
