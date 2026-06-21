"""
run_pipeline.py — One command to run the whole offline pipeline end to end:
    clean -> features -> impact models -> hotspot -> eval report

Usage (from theme2/):
    ../.venv/Scripts/python.exe run_pipeline.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STEPS = ["src.clean", "src.features", "src.impact_models", "src.hotspot", "src.eval"]


def main() -> None:
    for mod in STEPS:
        print(f"\n{'='*60}\n>>> {mod}\n{'='*60}")
        runpy.run_module(mod, run_name="__main__")
    print("\nPipeline complete. Models in models/, reports in reports/.")
    print("Serve API : ../.venv/Scripts/python.exe -m uvicorn api.main:app --port 8000")
    print("Dashboard : ../.venv/Scripts/python.exe -m streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
