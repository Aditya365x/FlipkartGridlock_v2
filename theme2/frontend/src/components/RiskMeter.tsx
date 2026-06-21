import { motion } from "framer-motion";
import type { RiskLevel } from "@/lib/types";
import { RISK_COLOR } from "@/lib/format";

interface RiskMeterProps {
  level: RiskLevel;
  score: number; // 0-100
  confidence?: string;
}

/** Radial risk gauge — the "what's the situation" hero indicator. */
export function RiskMeter({ level, score, confidence }: RiskMeterProps) {
  const color = RISK_COLOR[level];
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = (Math.min(score, 100) / 100) * circ;

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-[140px] w-[140px]">
        <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
          <circle cx="70" cy="70" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
          <motion.circle
            cx="70"
            cy="70"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 8px ${color})` }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="font-display text-3xl font-bold tabular-nums" style={{ color }}>
              {score.toFixed(0)}
            </div>
            <div className="text-[10px] uppercase tracking-widest text-ink-faint">/ 100</div>
          </div>
        </div>
      </div>
      <div
        className="mt-3 rounded-full px-4 py-1 text-sm font-bold tracking-wide"
        style={{ color, backgroundColor: `${color}1f`, boxShadow: `0 0 24px -6px ${color}` }}
      >
        {level} RISK
      </div>
      {confidence && (
        <div className="mt-2 text-[11px] text-ink-muted">
          Confidence: <span className="font-semibold text-ink">{confidence}</span>
        </div>
      )}
    </div>
  );
}
