"""
RailSynchro Solver Module: CP-SAT Joint Optimization & Siloed Baseline Engine
=============================================================================
Problem Statement: SIH26027 (Automatic Block Planning for Indian Railways)

This module implements two scheduling regimes:
1. Baseline ("Before"): The conventional siloed Indian Railways process where
   each engineering department (TMS, TDMS, SMMS) independently books track
   blocks at their own earliest feasible timetable window. Because requests
   are not merged, track downtime equals the sum of all individual durations.
   
2. Joint Optimization ("After"): A mathematically rigorous constraint optimization
   model built with Google OR-Tools CP-SAT:
   - Groups overlapping departmental requests by corridor.
   - Merges them into a single joint block whose duration = max(department durations).
   - Constrains the joint window to only start at hours that strictly avoid all
     COA train-occupied hours for that corridor.
   - Enforces a Divisional Resource Concurrency limit (e.g. max 2 simultaneous
     blocks division-wide) to reflect OHE power isolation and section controller limits.
   - Minimizes the urgency-weighted start times: high-urgency corridors (high defect
     severity + overdue days) are guaranteed earlier allocation.
"""

from typing import Dict, List, Any
import time
from ortools.sat.python import cp_model
from data import CORRIDORS, COA_TRAIN_OCCUPIED_HOURS, DEFECTS, HORIZON_HOURS
from scoring import compute_defect_risk_score

def get_defects_with_scores() -> List[Dict[str, Any]]:
    """Returns defects enriched with computed rule-based risk scores."""
    enriched = []
    for d in DEFECTS:
        score_info = compute_defect_risk_score(d)
        d_copy = dict(d)
        d_copy.update(score_info)
        enriched.append(d_copy)
    return enriched

def find_feasible_starts(corridor_id: str, duration: int, occupied_hours: List[int], horizon: int = HORIZON_HOURS) -> List[int]:
    """
    Finds all valid start hours t in [0, horizon - duration] such that
    no hour in [t, t + duration - 1] overlaps with a train-occupied hour.
    """
    occupied_set = set(occupied_hours)
    feasible = []
    for t in range(0, horizon - duration + 1):
        # Check if entire window [t, t + duration) is clear of trains
        window_clear = True
        for h in range(t, t + duration):
            if h in occupied_set:
                window_clear = False
                break
        if window_clear:
            feasible.append(t)
    return feasible

def compute_siloed_baseline(defects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simulates today's uncoordinated/siloed scheduling process:
    - Each department schedules its defect independently at the earliest train-free window.
    - No merging: each defect requires its own track closure.
    - Total downtime = sum of all individual defect durations.
    """
    siloed_blocks = []
    total_downtime = 0
    
    for d in defects:
        corridor_id = d["corridor"]
        occupied = COA_TRAIN_OCCUPIED_HOURS.get(corridor_id, [])
        duration = d["duration_hours"]
        feasible = find_feasible_starts(corridor_id, duration, occupied)
        
        earliest_start = feasible[0] if feasible else 0
        end_hour = earliest_start + duration
        total_downtime += duration
        
        siloed_blocks.append({
            "defect_id": d["id"],
            "department": d["department"],
            "corridor_id": corridor_id,
            "description": d["description"],
            "severity": d["severity"],
            "days_overdue": d["days_overdue"],
            "risk_score": d["risk_score"],
            "start_hour": earliest_start,
            "end_hour": end_hour,
            "duration_hours": duration,
            "start_day": (earliest_start // 24) + 1,
            "start_hour_in_day": earliest_start % 24,
            "is_merged": False
        })
        
    return {
        "blocks": siloed_blocks,
        "total_downtime_hours": total_downtime,
        "total_blocks_count": len(siloed_blocks)
    }

def solve_joint_optimization(defects: List[Dict[str, Any]], max_concurrent_blocks: int = 2) -> Dict[str, Any]:
    """
    Solves the joint block scheduling problem using Google OR-Tools CP-SAT.
    
    Mathematical Formulation:
      - Corridors C = {c_1, ..., c_m}
      - For each c in C:
          Defects D_c = {d in defects | d.corridor == c}
          Joint Duration W_c = max_{d in D_c}(d.duration_hours)
          Corridor Urgency U_c = sum_{d in D_c}(d.risk_score)
          Feasible Starts F_c = {t in [0, 168 - W_c] | [t, t + W_c - 1] ∩ Occupied_c = ∅}
          
      - Decision Variables:
          Start_c in F_c
          End_c = Start_c + W_c
          Interval_c = NewIntervalVar(Start_c, W_c, End_c)
          
      - Global Constraint (Divisional Resource Capacity):
          Cumulative(Interval_c, demand=1, capacity=max_concurrent_blocks)
          
      - Objective:
          Minimize sum_{c in C} round(U_c * 10) * Start_c
          (Prioritizes scheduling high-urgency corridors at the earliest available conflict-free slots)
    """
    start_time_wall = time.time()
    
    # 1. Group defects by corridor
    corridor_map: Dict[str, List[Dict[str, Any]]] = {}
    for d in defects:
        corridor_map.setdefault(d["corridor"], []).append(d)
        
    model = cp_model.CpModel()
    
    start_vars = {}
    end_vars = {}
    interval_vars = {}
    corridor_data = {}
    
    for cid, d_list in corridor_map.items():
        joint_duration = max(d["duration_hours"] for d in d_list)
        total_urgency = sum(d["risk_score"] for d in d_list)
        departments = sorted(list(set(d["department"] for d in d_list)))
        occupied = COA_TRAIN_OCCUPIED_HOURS.get(cid, [])
        
        feasible_starts = find_feasible_starts(cid, joint_duration, occupied)
        if not feasible_starts:
            raise ValueError(f"No feasible train-free window found for corridor {cid} with duration {joint_duration}h")
            
        # Decision variable: Start hour constrained to feasible domain
        start_var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(feasible_starts), f"start_{cid}"
        )
        end_var = model.NewIntVar(0, HORIZON_HOURS, f"end_{cid}")
        model.Add(end_var == start_var + joint_duration)
        
        interval_var = model.NewIntervalVar(start_var, joint_duration, end_var, f"interval_{cid}")
        
        start_vars[cid] = start_var
        end_vars[cid] = end_var
        interval_vars[cid] = interval_var
        
        corridor_data[cid] = {
            "joint_duration": joint_duration,
            "total_urgency": total_urgency,
            "departments": departments,
            "defects": d_list,
            "feasible_starts_count": len(feasible_starts)
        }
        
    # 2. Divisional Concurrency Constraint:
    # At most max_concurrent_blocks can be active across the division simultaneously
    model.AddCumulative(
        list(interval_vars.values()),
        [1] * len(interval_vars),
        max_concurrent_blocks
    )
    
    # 3. Objective: Minimize urgency-weighted start time
    # Corridors with high cumulative risk score get earliest slots
    model.Minimize(
        sum(int(round(corridor_data[cid]["total_urgency"] * 10)) * start_vars[cid] for cid in corridor_map)
    )
    
    # 4. Invoke CP-SAT Solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = 4
    
    status_code = solver.Solve(model)
    status_str = solver.StatusName(status_code)
    wall_time_ms = round((time.time() - start_time_wall) * 1000, 2)
    
    if status_str not in ("OPTIMAL", "FEASIBLE"):
        raise RuntimeError(f"CP-SAT solver returned non-solution status: {status_str}")
        
    # 5. Build solution schedule
    joint_blocks = []
    total_joint_downtime = 0
    
    # Sort corridors by assigned start hour
    sorted_corridors = sorted(corridor_map.keys(), key=lambda c: solver.Value(start_vars[c]))
    
    for cid in sorted_corridors:
        c_info = corridor_data[cid]
        start_val = int(solver.Value(start_vars[cid]))
        duration = c_info["joint_duration"]
        end_val = start_val + duration
        total_joint_downtime += duration
        
        corridor_meta = next((c for c in CORRIDORS if c["id"] == cid), {"name": cid, "zone": ""})
        
        joint_blocks.append({
            "corridor_id": cid,
            "corridor_name": corridor_meta["name"],
            "zone": corridor_meta["zone"],
            "start_hour": start_val,
            "end_hour": end_val,
            "duration_hours": duration,
            "start_day": (start_val // 24) + 1,
            "start_hour_in_day": start_val % 24,
            "departments_merged": c_info["departments"],
            "total_urgency": round(c_info["total_urgency"], 1),
            "defects_included": [
                {
                    "id": d["id"],
                    "department": d["department"],
                    "description": d["description"],
                    "severity": d["severity"],
                    "days_overdue": d["days_overdue"],
                    "duration_hours": d["duration_hours"],
                    "risk_score": d["risk_score"]
                }
                for d in c_info["defects"]
            ]
        })
        
    return {
        "blocks": joint_blocks,
        "total_downtime_hours": total_joint_downtime,
        "total_blocks_count": len(joint_blocks),
        "solver_telemetry": {
            "status": status_str,
            "wall_time_ms": wall_time_ms,
            "objective_value": solver.ObjectiveValue(),
            "num_branches": solver.NumBranches(),
            "num_conflicts": solver.NumConflicts(),
            "concurrency_limit": max_concurrent_blocks
        }
    }
