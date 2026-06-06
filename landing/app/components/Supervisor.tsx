"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { GraduationCap, User } from "lucide-react";

// =============================================================
//  EDIT SUPERVISOR HERE
//  Drop a photo at /public/team/supervisor.png to replace placeholder.
// =============================================================
const supervisor = {
  name: "DR. Ahmed Bin Mahfoudh",
  title: "Project Supervisor",
  affiliation: "Faculty of Computer & Information Technology",
  image: "/team/supervisor.png",
};
// =============================================================

export default function Supervisor() {
  const [imageOk, setImageOk] = useState(true);

  return (
    <section
      id="supervisor"
      className="relative py-20 sm:py-28 px-6 max-w-4xl mx-auto"
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-50px" }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="relative"
      >
        {/* Outer glow plate */}
        <div
          aria-hidden
          className="absolute -inset-1 rounded-3xl bg-gradient-to-br from-gold/30 via-transparent to-gold/10 blur-2xl opacity-50"
        />

        <div className="relative glass rounded-3xl p-8 sm:p-12 overflow-hidden">
          {/* Corner accents */}
          <div
            aria-hidden
            className="absolute top-0 left-0 h-12 w-12 border-l-2 border-t-2 border-gold rounded-tl-3xl"
          />
          <div
            aria-hidden
            className="absolute bottom-0 right-0 h-12 w-12 border-r-2 border-b-2 border-gold rounded-br-3xl"
          />

          {/* Subtle inner gradient */}
          <div
            aria-hidden
            className="absolute inset-0 -z-10"
            style={{
              background:
                "radial-gradient(circle at 20% 0%, rgba(212,175,55,0.08), transparent 60%)",
            }}
          />

          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-8">
            {/* Avatar */}
            <div className="relative shrink-0">
              <div
                aria-hidden
                className="absolute inset-0 rounded-full bg-gold/20 blur-2xl animate-pulse-glow"
              />
              <div className="relative h-32 w-32 sm:h-36 sm:w-36 rounded-full overflow-hidden ring-2 ring-gold/50 bg-gradient-to-br from-surface-2 to-surface">
                {imageOk ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={supervisor.image}
                    alt={supervisor.name}
                    className="h-full w-full object-cover"
                    onError={() => setImageOk(false)}
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-gold/40">
                    <User className="h-12 w-12" strokeWidth={1.5} />
                  </div>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="text-center sm:text-left flex-1">
              <div className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/5 px-4 py-1.5 mb-4">
                <GraduationCap className="h-4 w-4 text-gold" />
                <span className="mono-tag text-gold">Project Supervisor</span>
              </div>

              <h3 className="font-display font-bold text-2xl sm:text-3xl text-foreground mb-2">
                {supervisor.name}
              </h3>
              <p className="text-muted text-sm sm:text-base">
                {supervisor.affiliation}
              </p>

              <div className="mt-6 h-px w-full divider-gold" />

              <p className="mt-6 text-muted leading-relaxed text-sm">
                Guiding the technical direction, scope, and academic rigor of
                Eqaab — from system architecture through to final defense.
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
