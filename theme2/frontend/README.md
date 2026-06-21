# EVENT Shield AI — Command Center (Frontend)

Mission-critical traffic-intelligence dashboard. React + TypeScript + Tailwind + Framer Motion + Recharts, talking to the FastAPI backend.

## Run (two terminals)

**1. Backend** (from `theme2/`):
```bash
../.venv/Scripts/python.exe -m uvicorn api.main:app --port 8000
```

**2. Frontend** (from `theme2/frontend/`):
```bash
npm install      # first time only
npm run dev      # http://localhost:5173
```
Vite proxies `/api/*` → `http://127.0.0.1:8000`, so no CORS/config needed in dev.
For production, set `VITE_API_URL` to the API origin and run `npm run build`.

## Architecture
```
src/
  lib/        api client, types, formatters, useAsync hook
  components/
    layout/   Sidebar, TopBar, AppShell
    ui/       Panel (glass), Badge
    *         KpiCard, RiskMeter, AlertsPanel, ActionPlanCard,
              CorridorLoadList, LoadBarChart, TacticalMap
  pages/      CommandCenter (hero), EventSimulation, TrafficForecast,
              ResourcePlanner, PostEventAnalytics
```

## Backend endpoints consumed
- `GET  /dashboard`     — command-center snapshot (KPIs, alerts, actions, deployment, top corridors)
- `POST /action_plan`   — full what-if: prediction + risk + confidence + alerts + plan
- `POST /forecast`      — expected corridor load for a time window
- `GET  /meta`          — dropdown vocab (types, causes, corridors, zones)

## Design system
Deep-navy glassmorphism, neon brand/cyan accents, semantic risk colors
(green→amber→orange→red), `Space Grotesk` for numerics + `Inter` for UI.
Tokens live in `tailwind.config.ts`; surfaces use the `.glass` utility in `index.css`.

## Notes
- The map is a self-contained stylized SVG (no Mapbox token, works offline).
  Swap `TacticalMap` for `react-leaflet` + CARTO dark tiles for live geography.
- Post-Event Learning shows latest offline metrics; wire a `/learning` endpoint to stream live calibration.
