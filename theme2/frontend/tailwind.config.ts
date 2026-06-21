import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // command-center palette
        bg: { DEFAULT: "#070b14", soft: "#0a1020", panel: "#0e1626" },
        ink: { DEFAULT: "#e6edf7", muted: "#8aa0bd", faint: "#5b6b85" },
        brand: { DEFAULT: "#3b82f6", bright: "#60a5fa", cyan: "#22d3ee" },
        danger: "#ef4444",
        warn: "#f97316",
        amber: "#eab308",
        safe: "#22c55e",
        line: "rgba(96,165,250,0.14)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "Inter", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(96,165,250,0.18), 0 8px 40px -12px rgba(37,99,235,0.45)",
        "glow-danger": "0 0 0 1px rgba(239,68,68,0.35), 0 8px 40px -10px rgba(239,68,68,0.5)",
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(96,165,250,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(96,165,250,0.05) 1px, transparent 1px)",
      },
      keyframes: {
        pulseDot: {
          "0%,100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.45", transform: "scale(0.8)" },
        },
        ping2: {
          "0%": { transform: "scale(1)", opacity: "0.6" },
          "100%": { transform: "scale(2.6)", opacity: "0" },
        },
        sweep: { "0%": { left: "-30%" }, "100%": { left: "130%" } },
        rise: { "0%": { opacity: "0", transform: "translateY(8px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
      },
      animation: {
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
        ping2: "ping2 2s cubic-bezier(0,0,0.2,1) infinite",
        sweep: "sweep 2.4s linear infinite",
        rise: "rise 0.4s ease-out both",
      },
    },
  },
  plugins: [],
} satisfies Config;
