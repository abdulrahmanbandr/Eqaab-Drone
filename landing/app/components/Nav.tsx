"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";

const NAV = [
  { href: "#about", label: "About" },
  { href: "#features", label: "Features" },
  { href: "#architecture", label: "Architecture" },
  { href: "#team", label: "Team" },
];

// Mobile dropdown also surfaces Supervisor (it's a desktop-only CTA otherwise).
const MOBILE_NAV = [...NAV, { href: "#supervisor", label: "Supervisor" }];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, delay: 0.2 }}
      className="fixed inset-x-0 top-0 z-50"
    >
      <div
        className={`mx-auto max-w-6xl mt-4 px-4 sm:px-6 transition-all duration-500 ${
          scrolled ? "scale-[0.985]" : "scale-100"
        }`}
      >
        <div
          className={`flex items-center justify-between rounded-full px-5 py-3 transition-all duration-500 ${
            scrolled
              ? "glass border-gold/20 shadow-[0_8px_30px_-12px_rgba(0,0,0,0.6)]"
              : "border border-transparent"
          }`}
        >
          {/* Brand */}
          <a href="#hero" className="flex items-center gap-2">
            <span
              dir="rtl"
              lang="ar"
              className="font-arabic text-2xl font-bold text-gradient-gold leading-tight"
            >
              عقاب
            </span>
            <span className="hidden sm:inline mono-tag text-muted">EQAAB</span>
          </a>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV.map((n) => (
              <a
                key={n.href}
                href={n.href}
                className="mono-tag text-muted hover:text-gold transition-colors px-4 py-2 rounded-full hover:bg-gold/5"
              >
                {n.label}
              </a>
            ))}
          </nav>

          {/* CTA / Burger */}
          <div className="flex items-center gap-2">
            <a
              href="#supervisor"
              className="hidden sm:inline-flex mono-tag rounded-full bg-gold px-4 py-2 text-background font-semibold hover:shadow-[0_0_24px_-4px_rgba(212,175,55,0.6)] transition-all"
            >
              Supervisor
            </a>
            <button
              type="button"
              aria-label="Toggle menu"
              onClick={() => setOpen((v) => !v)}
              className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-full border border-gold/20 text-gold hover:border-gold/50 transition-colors"
            >
              {open ? (
                <X className="h-4 w-4" />
              ) : (
                <Menu className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="md:hidden mt-2 glass rounded-2xl p-2 flex flex-col"
            >
              {MOBILE_NAV.map((n) => (
                <a
                  key={n.href}
                  href={n.href}
                  onClick={() => setOpen(false)}
                  className="mono-tag text-muted hover:text-gold transition-colors px-4 py-3 rounded-xl hover:bg-gold/5"
                >
                  {n.label}
                </a>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.header>
  );
}
