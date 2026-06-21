# 🚦 EVENT Shield AI — Event Traffic Intelligence

AI-powered forecasting & resource optimization for **event-driven traffic congestion**, built on the
real **ASTraM** event log (Bengaluru · 8,173 events · Nov 2023 – Apr 2024).

It **quantifies an event's impact in advance**, recommends **optimal manpower / barricades / diversions**,
and **learns from every event** — a single product with a **FastAPI** backend and a **React** command-center UI.

> **Live demo (Hugging Face Space):** `https://huggingface.co/spaces/adityaXXXXXX/flipkartGridlock`

---

## ✅ Prerequisites

| You need | Why |
|---|---|
| **Git + Git LFS** | **Required.** Trained models & data are stored via Git LFS. Without LFS you get tiny pointer files and the app won't start. |
| **Docker Desktop** *(Option A)* | One-command run, mirrors the live Space. |
| **Python 3.11+ and Node 18+** *(Option B)* | To run backend + frontend directly. |

Install Git LFS once (if you don't have it): https://git-lfs.com → then `git lfs install`.

---

## 0. Clone the repo (with LFS — important!)

```bash
git lfs install
git clone https://github.com/Aditya365x/FlipkartGridlock_v2.git
cd FlipkartGridlock_v2
git lfs pull          # pulls the real model/data binaries (not pointers)
```

> If you cloned **before** installing LFS, just run `git lfs install && git lfs pull` inside the folder.
> Sanity check: `ls -lh theme2/models` — `*.joblib` files should be ~1–3 MB each (not ~130 bytes).

---

## ▶️ Option A — Docker (recommended, one command)

Builds the React app and serves it **together with the API** on one port — identical to the deployed Space.

```bash
docker build -t event-shield .
docker run -p 7860:7860 event-shield
```

Open **http://localhost:7860**

---

## ▶️ Option B — Run locally (two terminals)

**Terminal 1 — backend (FastAPI):**
```bash
cd theme2
python -m venv .venv

# activate the venv:
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   macOS / Linux:         source .venv/bin/activate

pip install -r requirements-api.txt
python -m uvicorn api.main:app --port 8000
```

**Terminal 2 — frontend (React):**
```bash
cd theme2/frontend
npm install
npm run dev
```

Open **http://localhost:5173**
*(The dev server automatically proxies API calls to the backend on port 8000 — both must be running.)*

---

## ▶️ Option C — Streamlit dashboard (original prototype, optional)

The same models also power a Streamlit dashboard:
```bash
cd theme2
pip install -r requirements.txt          # full deps (includes Streamlit, plotly, pydeck)
streamlit run dashboard/app.py
```

---

## 🧭 What to evaluate (suggested 3-minute flow)

1. **Command Center** — live operational picture: KPIs, interactive map, Active Events roster, alerts, AI action plan.
2. **Event Planner** — click the **Accident → Political Rally → Festival** presets; watch risk scale MEDIUM → HIGH → CRITICAL with full action plans. Then **📝 Log for post-event review**.
3. **Resource Planner** — deployment for your planned event; drag the **officer slider** to re-optimize live; see barricades + the diversion playbook.
4. **Traffic Forecast** & **Live Map** — expected corridor load by day/time on a pannable map.
5. **Post-Event Learning** — click **Seed 30 real events** → the model recalibrates from real outcomes (closure accuracy, clearance error) **live**.

---

## 🔁 (Optional) Retrain the models from scratch

Models are committed, so this is **not** required — but to rebuild everything from the raw CSV:
```bash
cd theme2
pip install -r requirements.txt
python run_pipeline.py        # cleans data, builds features, trains all models
```

---

## 🗂️ Project structure

```
.
├── Dockerfile                 # single-service image (React build + FastAPI)
├── README.md                  # this file (also the HF Space config)
└── theme2/
    ├── api/main.py            # FastAPI: prediction, deployment, forecast, learning endpoints
    ├── src/                   # ML engine: clean, features, models, serve, recommend, decision, feedback
    ├── frontend/              # React + TypeScript + Tailwind command-center UI
    ├── dashboard/app.py       # Streamlit dashboard (original prototype)
    ├── models/                # trained models (Git LFS)
    ├── data/                  # ASTraM data + processed parquet (Git LFS)
    ├── reports/EVALUATION.md  # model metrics & methodology
    ├── tests/test_core.py     # regression tests
    └── run_pipeline.py        # end-to-end training pipeline
```

Run the tests:
```bash
cd theme2 && python tests/test_core.py     # or: pytest tests/
```

---

## 🩹 Troubleshooting

- **App starts but predictions fail / "model not found":** Git LFS wasn't pulled — run `git lfs install && git lfs pull`.
- **Port already in use:** change it — `uvicorn api.main:app --port 8001` (and update the frontend) or `docker run -p 8080:7860 …`.
- **Map tiles are blank:** the map needs internet for street tiles; markers still render offline.
- **`npm run dev` can't reach the API:** make sure the backend is running on port 8000 (Option B).
- **LightGBM load error on Linux:** install `libgomp1` (`sudo apt-get install libgomp1`) — already handled in Docker.

---

## 📌 Honest scope
Built on the **real ASTraM historical dataset**. Road-closure probabilities are **calibrated**; the
forecaster is a typical-load model that's architecture-ready for a live feed; diversions surface **real
historical closures** (the dataset has no route data) rather than fabricated routes. See
`theme2/reports/EVALUATION.md` for full metrics and methodology.
