---
title: EVENT Shield AI
emoji: 🚦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# EVENT Shield AI — Event Traffic Intelligence

AI-powered forecasting & resource optimization for event-driven traffic congestion, built on the
real ASTraM event log (Bengaluru · 8,173 events · Nov 2023 – Apr 2024).

A single Docker service: **FastAPI** serves the ML API **and** the built **React** command center on
one port (7860).

## What it does
- **Forecasts event impact** — calibrated road-closure probability, impact duration, risk level.
- **Recommends deployment** — OR-Tools officer allocation, barricades, and a historical-closure
  diversion playbook.
- **Learns after events** — an online calibration loop that improves predictions from real outcomes.

## Modules
Command Center · Event Planner (what-if) · Resource Planner · Traffic Forecast · Live Map ·
Post-Event Learning.

## Run locally (two terminals)
```bash
# backend (from theme2/)
python -m uvicorn api.main:app --port 8000
# frontend (from theme2/frontend/)
npm install && npm run dev          # http://localhost:5173
```

## Run as one service (like the Space)
```bash
docker build -t event-shield .
docker run -p 7860:7860 event-shield   # http://localhost:7860
```

> Note: trained models and processed data are committed, so it runs without retraining.
> Honest scope: built on historical data; the forecaster is architecture-ready for a live feed.
