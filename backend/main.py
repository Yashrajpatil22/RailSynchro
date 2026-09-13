"""
RailSynchro FastAPI Application: AI-Powered Automatic Block Planning for Indian Railways
========================================================================================
Problem Statement: SIH26027

REST API Endpoints:
  - GET /api/health: Health check and service metadata
  - GET /api/defects: Returns corridor metadata, COA train-occupied timetable map,
                      and defects with explainable rule-based risk scores
  - GET /api/schedule: Runs both the naive siloed baseline and Google OR-Tools CP-SAT
                       joint optimization, returning before/after schedules, total downtime,
                       and reduction metrics
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional

from data import CORRIDORS, COA_TRAIN_OCCUPIED_HOURS, HORIZON_HOURS
from solver import get_defects_with_scores, compute_siloed_baseline, solve_joint_optimization

app = FastAPI(
    title="RailSynchro API — Automatic Block Planning (SIH26027)",
    description=(
        "Production MVP constraint optimization engine for Indian Railways. "
        "Coordinates Track (TMS), Traction (TDMS), and Signalling (SMMS) maintenance requests "
        "against COA train timetable paths using Google OR-Tools CP-SAT."
    ),
    version="1.0.0"
)

# Enable CORS for all origins so frontend deployed on Vercel/local can communicate freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint for cloud service monitoring (e.g. Render)."""
    return {
        "status": "healthy",
        "service": "RailSynchro Optimization Engine",
        "version": "1.0.0",
        "sih_problem_code": "SIH26027",
        "supported_departments": ["TMS", "TDMS", "SMMS"],
        "solver_backend": "Google OR-Tools CP-SAT"
    }

@app.get("/api/defects")
def get_defects_endpoint() -> Dict[str, Any]:
    """
    Returns:
      - All sample defects enriched with transparent, explainable rule-based risk scores
      - 5 track corridors with railway zone and technical attributes
      - 7-day (168-hour) scheduling horizon configuration
      - Per-corridor COA timetable occupied hours map
    """
    try:
        defects = get_defects_with_scores()
        return {
            "horizon_hours": HORIZON_HOURS,
            "corridors": CORRIDORS,
            "train_occupied_hours": COA_TRAIN_OCCUPIED_HOURS,
            "defects": defects,
            "total_defects": len(defects)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule")
def get_schedule_endpoint(
    max_concurrent_blocks: int = Query(
        default=2,
        ge=1,
        le=5,
        description="Maximum simultaneous maintenance blocks allowed division-wide"
    )
) -> Dict[str, Any]:
    """
    Solves the block planning problem:
    1. Computes the 'Before' baseline (siloed, unmerged departmental requests).
    2. Runs the 'After' CP-SAT joint optimization engine (merging overlapping corridor
       requests into single joint windows, avoiding COA train conflicts, minimizing
       urgency-weighted start hours).
    3. Returns comparative KPIs: downtime reduction (hours and %), block closure reduction.
    """
    try:
        defects = get_defects_with_scores()
        
        # 1. Siloed Baseline ("Before")
        baseline_result = compute_siloed_baseline(defects)
        
        # 2. CP-SAT Joint Optimization ("After")
        joint_result = solve_joint_optimization(
            defects,
            max_concurrent_blocks=max_concurrent_blocks
        )
        
        # 3. Comparative Analytics
        downtime_before = baseline_result["total_downtime_hours"]
        downtime_after = joint_result["total_downtime_hours"]
        downtime_saved = downtime_before - downtime_after
        reduction_pct = round((downtime_saved / downtime_before) * 100, 2) if downtime_before > 0 else 0.0
        
        blocks_before = baseline_result["total_blocks_count"]
        blocks_after = joint_result["total_blocks_count"]
        blocks_saved = blocks_before - blocks_after
        blocks_reduction_pct = round((blocks_saved / blocks_before) * 100, 2) if blocks_before > 0 else 0.0
        
        return {
            "horizon_hours": HORIZON_HOURS,
            "corridors": CORRIDORS,
            "train_occupied_hours": COA_TRAIN_OCCUPIED_HOURS,
            "defects": defects,
            "summary": {
                "downtime_before_hours": downtime_before,
                "downtime_after_hours": downtime_after,
                "downtime_saved_hours": downtime_saved,
                "downtime_reduction_pct": reduction_pct,
                "blocks_count_before": blocks_before,
                "blocks_count_after": blocks_after,
                "blocks_reduction_pct": blocks_reduction_pct,
                "solver_status": joint_result["solver_telemetry"]["status"],
                "solve_time_ms": joint_result["solver_telemetry"]["wall_time_ms"]
            },
            "baseline_schedule": baseline_result,
            "joint_schedule": joint_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static frontend directory if present (serves index.html and config.js directly)
import os
from fastapi.staticfiles import StaticFiles

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

