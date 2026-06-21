import { motion } from "framer-motion";
import { Users, Construction, Route, Ambulance, Radio, Eye, CheckCircle2 } from "lucide-react";
import type { ComponentType } from "react";

const ICONS: { match: RegExp; icon: ComponentType<{ className?: string }>; tone: string }[] = [
  { match: /officer|deploy/i, icon: Users, tone: "text-brand-bright" },
  { match: /barricade/i, icon: Construction, tone: "text-warn" },
  { match: /diversion|route/i, icon: Route, tone: "text-brand-cyan" },
  { match: /emergency|ambulance|tow/i, icon: Ambulance, tone: "text-danger" },
  { match: /control room|incident command|brief/i, icon: Radio, tone: "text-amber" },
  { match: /monitor|verify/i, icon: Eye, tone: "text-ink-muted" },
];

function pick(action: string) {
  return ICONS.find((x) => x.match.test(action)) ?? { icon: CheckCircle2, tone: "text-safe" };
}

// strip the **bold** markers the backend emits
const clean = (s: string) => s.replace(/\*\*/g, "");

export function ActionPlanCard({ actions }: { actions: string[] }) {
  return (
    <ol className="space-y-2">
      {actions.map((a, i) => {
        const { icon: Icon, tone } = pick(a);
        return (
          <motion.li
            key={i}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06 }}
            className="flex items-center gap-3 rounded-xl border border-line bg-white/[0.03] px-3 py-2.5 transition hover:border-brand/30 hover:bg-white/[0.06]"
          >
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/5">
              <Icon className={`h-4 w-4 ${tone}`} />
            </span>
            <span className="text-sm text-ink">{clean(a)}</span>
          </motion.li>
        );
      })}
    </ol>
  );
}
