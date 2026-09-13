import urllib.request
import json

def verify():
    url = "http://127.0.0.1:8000/api/schedule"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode())
    
    print("==================================================================")
    print("          RAILSYNCHRO ENGINE: CP-SAT SOLVER VERIFICATION           ")
    print("==================================================================")
    print(f"Solver Status  : {data['summary']['solver_status']}")
    print(f"Solve Time     : {data['summary']['solve_time_ms']} ms")
    print(f"Downtime Before: {data['summary']['downtime_before_hours']} hours (Siloed)")
    print(f"Downtime After : {data['summary']['downtime_after_hours']} hours (Joint Optimized)")
    print(f"Downtime Saved : {data['summary']['downtime_saved_hours']} hours (-{data['summary']['downtime_reduction_pct']}%)")
    print(f"Block Closures : {data['summary']['blocks_count_before']} blocks -> {data['summary']['blocks_count_after']} joint windows (-{data['summary']['blocks_reduction_pct']}%)")
    print("\n--- OPTIMIZED CORRIDOR SCHEDULE (AFTER) ---")
    for b in data['joint_schedule']['blocks']:
        print(f"[{b['corridor_id']}] {b['corridor_name']}")
        print(f"   Window : Day {b['start_day']}, {b['start_hour_in_day']:02d}:00 to {b['start_hour_in_day'] + b['duration_hours']:02d}:00 (Duration: {b['duration_hours']}h)")
        print(f"   Merged : {', '.join(b['departments_merged'])}")
        print(f"   Defects: {[d['id'] for d in b['defects_included']]}")
        print(f"   Urgency: {b['total_urgency']} pts")
    print("==================================================================")

if __name__ == "__main__":
    verify()
