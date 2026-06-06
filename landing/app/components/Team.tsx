"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { User } from "lucide-react";
import SectionHeading from "./SectionHeading";

// LinkedIn glyph (lucide-react no longer ships brand icons).
function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z" />
    </svg>
  );
}

// =============================================================
//  EDIT TEAM MEMBERS HERE
//  - Replace `name` and `role` with real values
//  - Drop each member's photo at /public/team/memberN.png
//    (any square format works; ~512x512 recommended)
//  - Cards show a graceful placeholder avatar until photos exist
//
//  ▶ LinkedIn button:
//    Paste each member's LinkedIn profile URL into `linkedin`.
//    Example:  linkedin: "https://www.linkedin.com/in/john-doe"
//    Leave it as an empty string ("") to hide the button for that member.
// =============================================================
type TeamMember = {
  name: string;
  role: string;
  image: string;
  linkedin: string; // <-- paste full LinkedIn profile URL here, or "" to hide
};

const team: TeamMember[] = [
  {
    name: "Abdulrahman Bandr Al-dahhas",
    role: "AI & Cloud Engineer",
    image: "/team/member1.png",
    linkedin: "https://www.linkedin.com/in/abdulrahman-aldahhas-22b37a274",
  },
  {
    name: "Turki Faris Al-holaifi",
    role: "Data Engineer",
    image: "/team/member2.png",
    linkedin: "https://www.linkedin.com/in/turki-al-holife-5b4a673b7/",
  },
  {
    name: "Rayan Abdullah Al-Ghamdi",
    role: "Data engineer & robots",
    image: "/team/member3-v2.png",
    linkedin: "https://www.linkedin.com/in/rayan-alghamdi-b553532b3/",
  },
  {
    name: "Saeed Saad Al-harthi",
    role: "Network Engineer & Cybersecurity",
    image: "/team/member4.png",
    linkedin: "https://www.linkedin.com/in/sbsal7/",
  },
  {
    name: "Mohammed Faisal Al-Sharif",
    role: "Software Engineer",
    image: "/team/member5.png",
    linkedin: "https://www.linkedin.com/in/محمد-الشريف-431a56407/",
  },
  {
    name: "Hossain Abdulqadder Al-Hubailee",
    role: "Hardware Integration",
    image: "/team/member6.png",
    linkedin: "https://www.linkedin.com/in/حسين-الهبيلي-836445408/",
  },
  {
    name: "Omar Abdullah Al-Enazi",
    role: "Embedded Systems Engineer",
    image: "/team/member7.png",
    linkedin: "https://www.linkedin.com/in/omar-al-enazi-092430363/",
  },
];
// =============================================================

export default function Team() {
  return (
    <section
      id="team"
      className="relative py-28 sm:py-36 px-6 max-w-7xl mx-auto"
    >
      <SectionHeading
        eyebrow="04 / The Team"
        title={
          <>
            Seven engineers.{" "}
            <span className="text-gradient-gold">One mission.</span>
          </>
        }
        description="Cross-disciplinary team spanning AI, embedded systems, flight controls, and full-stack engineering."
      />

      <div className="grid gap-5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {team.map((member, i) => (
          <TeamCard key={i} member={member} index={i} />
        ))}
      </div>
    </section>
  );
}

function TeamCard({
  member,
  index,
}: {
  member: TeamMember;
  index: number;
}) {
  const [imageOk, setImageOk] = useState(true);

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{
        duration: 0.6,
        delay: (index % 4) * 0.08,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="glass glass-hover relative overflow-hidden rounded-2xl p-6 group"
    >
      <div className="relative mx-auto mb-5 h-28 w-28">
        {/* Glow halo */}
        <div
          aria-hidden
          className="absolute inset-0 rounded-full bg-gradient-to-br from-gold/30 to-gold/0 blur-xl opacity-60 group-hover:opacity-100 transition-opacity"
        />
        <div className="relative h-28 w-28 rounded-full overflow-hidden ring-1 ring-gold/30 group-hover:ring-gold/70 transition-all bg-gradient-to-br from-surface-2 to-surface">
          {imageOk ? (
            // Plain <img> avoids next/image optimizer errors when placeholder
            // files don't exist yet. Swap to next/image once photos are dropped in.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={member.image}
              alt={member.name}
              className="h-full w-full object-cover"
              onError={() => setImageOk(false)}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-gold/40">
              <User className="h-10 w-10" strokeWidth={1.5} />
            </div>
          )}
        </div>
      </div>

      <div className="text-center">
        <h3 className="font-display font-semibold text-base text-foreground">
          {member.name}
        </h3>
        <p className="mono-tag mt-1 text-gold/70">{member.role}</p>

        {/* LinkedIn button — only renders when a URL is provided. */}
        {member.linkedin && (
          <a
            href={member.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${member.name} on LinkedIn`}
            title="Open LinkedIn profile"
            className="mt-4 inline-flex h-9 w-9 items-center justify-center rounded-full border border-gold/30 bg-gold/5 text-gold/80 transition-all hover:border-gold/70 hover:bg-gold/15 hover:text-gold hover:shadow-[0_0_18px_-4px_rgba(212,175,55,0.55)]"
          >
            <LinkedInIcon className="h-4 w-4" />
          </a>
        )}
      </div>
    </motion.div>
  );
}
