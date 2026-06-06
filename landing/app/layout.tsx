import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  display: "swap",
});

// Thmanyah Serif Display — for the headline عقاب and any large Arabic display text.
// Files live in app/fonts/thmanyah/ (self-hosted, embedded by Next.js at build time).
const thmanyahDisplay = localFont({
  variable: "--font-thmanyah-display",
  display: "swap",
  src: [
    { path: "./fonts/thmanyah/thmanyahserifdisplay-Light.woff2", weight: "300", style: "normal" },
    { path: "./fonts/thmanyah/thmanyahserifdisplay-Regular.woff2", weight: "400", style: "normal" },
    { path: "./fonts/thmanyah/thmanyahserifdisplay-Medium.woff2", weight: "500", style: "normal" },
    { path: "./fonts/thmanyah/thmanyahserifdisplay-Bold.woff2", weight: "700", style: "normal" },
    { path: "./fonts/thmanyah/thmanyahserifdisplay-Black.woff2", weight: "900", style: "normal" },
  ],
});

// Thmanyah Sans — for any Arabic UI / body text.
const thmanyahSans = localFont({
  variable: "--font-thmanyah-sans",
  display: "swap",
  src: [
    { path: "./fonts/thmanyah/thmanyahsans-Regular.woff2", weight: "400", style: "normal" },
    { path: "./fonts/thmanyah/thmanyahsans-Medium.woff2", weight: "500", style: "normal" },
    { path: "./fonts/thmanyah/thmanyahsans-Bold.woff2", weight: "700", style: "normal" },
  ],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://eqaab.vercel.app"),
  title: "Eqaab (عقاب) — Autonomous AI-Powered Surveillance Drone",
  description:
    "Eqaab — an autonomous AI-powered object tracking drone for smart surveillance. From Saudi engineers to the world.",
  keywords: [
    "Eqaab",
    "عقاب",
    "Saudi drone",
    "AI surveillance",
    "autonomous drone",
    "object tracking",
    "graduation project",
  ],
  authors: [{ name: "Eqaab Team" }],
  openGraph: {
    title: "Eqaab (عقاب) — Autonomous AI-Powered Surveillance Drone",
    description:
      "Autonomous AI-powered object tracking drone for smart surveillance. From Saudi engineers to the world.",
    url: "/",
    siteName: "Eqaab",
    images: [
      {
        url: "/logo.png",
        width: 1024,
        height: 1024,
        alt: "Eqaab Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Eqaab (عقاب) — Autonomous AI-Powered Surveillance Drone",
    description:
      "Autonomous AI-powered object tracking drone for smart surveillance.",
    images: ["/logo.png"],
  },
  icons: {
    // Favicon: prefer the SVG that always ships, then fall back to PNG when present.
    icon: [
      { url: "/logo.svg", type: "image/svg+xml" },
      { url: "/logo.png", type: "image/png" },
    ],
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#030305",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} ${thmanyahDisplay.variable} ${thmanyahSans.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
