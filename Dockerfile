# ===== EVENT Shield AI — single-service image (FastAPI serves API + built React app) =====
# Build context = repo root (gridLockProject). Designed for Hugging Face Spaces (Docker SDK, port 7860).

# ---- stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY theme2/frontend/package.json theme2/frontend/package-lock.json ./
RUN npm ci
COPY theme2/frontend/ ./
# same-origin API in production (FastAPI serves this build), so the client calls "/dashboard" etc.
ENV VITE_API_URL=""
RUN npm run build

# ---- stage 2: python runtime ----
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# libgomp1 is required by lightgbm
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY theme2/requirements-api.txt ./requirements-api.txt
RUN pip install -r requirements-api.txt

# app code + committed models/data (so it runs without retraining)
COPY theme2/ ./theme2/
# drop in the built frontend where FastAPI looks for it
COPY --from=frontend /fe/dist ./theme2/frontend/dist

# HF Spaces run as a non-root user — make the runtime-written dirs writable
# (feedback log + learned calibration.json)
RUN chmod -R 777 theme2/data theme2/models

ENV HOME=/app
WORKDIR /app/theme2
EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
