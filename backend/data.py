"""
RailSynchro Data Module: Synthetic Indian Railways Infrastructure & COA Timetable Data
======================================================================================
Problem Statement: SIH26027 (AI-Powered Automatic Block Planning for Indian Railways)

This module provides synthetic yet realistic data simulating:
1. Five strategic Indian Railways track corridors (Northern, North Central, and Central zones).
2. A 7-day (168-hour) scheduling horizon with COA (Control Office Application) timetable occupancy.
   - Occupied hours model passenger express and freight paths where track blocks are strictly prohibited.
   - Critical constraint: corridors feature occupied hours right at the start of the horizon
     (hours 0-6), ensuring the optimization solver cannot trivially schedule at hour 0.
3. 12 sample maintenance defects across the three core engineering departments:
   - TMS: Track Management System (Permanent Way / civil engineering)
   - TDMS: Traction Distribution Management System (Overhead 25kV OHE power)
   - SMMS: Signalling & Telecommunication Maintenance Management System
"""

from typing import List, Dict, Any

HORIZON_HOURS = 168  # 7 days * 24 hours (Day 1 H0 to Day 7 H167)

# 5 High-density Indian Railway corridors
CORRIDORS = [
    {
        "id": "COR-01",
        "name": "KM 40-45 (Ghaziabad - Hapur)",
        "zone": "Northern Railway (NR)",
        "section": "Delhi Division",
        "track_type": "Double Line Electrified (25kV AC)",
        "max_speed_kmh": 130
    },
    {
        "id": "COR-02",
        "name": "KM 60-65 (Kanpur - Unnao)",
        "zone": "North Central Railway (NCR)",
        "section": "Prayagraj Division",
        "track_type": "Quadruple Line Electrified (25kV AC)",
        "max_speed_kmh": 130
    },
    {
        "id": "COR-03",
        "name": "KM 85-90 (Prayagraj - Naini)",
        "zone": "North Central Railway (NCR)",
        "section": "Prayagraj Division",
        "track_type": "Double Line Electrified (Heavy Freight)",
        "max_speed_kmh": 110
    },
    {
        "id": "COR-04",
        "name": "KM 110-115 (Itarsi - Hoshangabad)",
        "zone": "West Central Railway (WCR)",
        "section": "Bhopal Division",
        "track_type": "Double Line Electrified (Grand Trunk Route)",
        "max_speed_kmh": 130
    },
    {
        "id": "COR-05",
        "name": "KM 130-135 (Nagpur - Wardha)",
        "zone": "Central Railway (CR)",
        "section": "Nagpur Division",
        "track_type": "Triple Line Electrified (Coal/Freight Corridor)",
        "max_speed_kmh": 120
    }
]

def _generate_coa_occupied_hours() -> Dict[str, List[int]]:
    """
    Generates realistic COA timetable occupied hours per corridor over 168 hours.
    Each corridor reflects realistic train passage peaks (morning Rajdhani/Shatabdi,
    intercity expresses, evening mail, and night freight paths).
    
    Occupied hours are distinct per corridor and intentionally include hours at the
    beginning of the horizon to force the solver to shift start times realistically.
    """
    occupied: Dict[str, set] = {c["id"]: set() for c in CORRIDORS}
    
    for day in range(7):
        base = day * 24
        
        # COR-01 (Ghaziabad-Hapur):
        # Heavy morning suburban + express rakes (0-4 occupied!)
        # Midday passenger slots: 10, 11, 12
        # Evening commuter rush: 17, 18, 19, 20
        # Night express passages: 23
        for h in [0, 1, 2, 3, 4, 10, 11, 12, 17, 18, 19, 20, 23]:
            occupied["COR-01"].add(base + h)
            
        # COR-02 (Kanpur-Unnao):
        # Busy corridor; early morning Vande Bharat/Shatabdi movements: 0, 1, 2, 3
        # Afternoon freight paths: 13, 14, 15
        # Evening express convoy: 21, 22
        for h in [0, 1, 2, 3, 13, 14, 15, 21, 22]:
            occupied["COR-02"].add(base + h)
            
        # COR-03 (Prayagraj-Naini):
        # Heavy freight corridor + DFC feeder. Early morning dense freight: 0, 1, 2, 3, 4, 5, 6!
        # Afternoon passenger rush: 14, 15, 16
        # Late night passenger: 22, 23
        for h in [0, 1, 2, 3, 4, 5, 6, 14, 15, 16, 22, 23]:
            occupied["COR-03"].add(base + h)
            
        # COR-04 (Itarsi-Hoshangabad):
        # Grand trunk junction line. Hour 0 free, but hours 1, 2, 3, 4, 5 blocked by South-bound expresses!
        # Midday trains: 11, 12, 13
        # Evening trains: 18, 19, 20
        for h in [1, 2, 3, 4, 5, 11, 12, 13, 18, 19, 20]:
            occupied["COR-04"].add(base + h)
            
        # COR-05 (Nagpur-Wardha):
        # Coal rakes & central passenger trains.
        # Early hours: 0, 1, 2
        # Midday: 9, 10, 11
        # Evening: 16, 17, 18, 19
        for h in [0, 1, 2, 9, 10, 11, 16, 17, 18, 19]:
            occupied["COR-05"].add(base + h)
            
    # Add slight day-specific special train / weekend freight variations
    # Weekend extra specials (Day 5 and Day 6):
    for d in [5, 6]:
        b = d * 24
        occupied["COR-01"].update([b + 7, b + 8])
        occupied["COR-02"].update([b + 8, b + 9])
        occupied["COR-04"].update([b + 7, b + 8])
        
    return {cid: sorted(list(hours)) for cid, hours in occupied.items()}

COA_TRAIN_OCCUPIED_HOURS = _generate_coa_occupied_hours()

# 12 Sample Defects distributed across TMS, TDMS, and SMMS
# Designed such that corridors have 2-3 overlapping departmental requests
DEFECTS: List[Dict[str, Any]] = [
    # --- Corridor 1: KM 40-45 (Ghaziabad - Hapur) ---
    {
        "id": "DEF-001",
        "department": "TMS",
        "corridor": "COR-01",
        "description": "Deep screening & tamping of ballast near crossover turnout",
        "severity": 4,
        "days_overdue": 6,
        "duration_hours": 4
    },
    {
        "id": "DEF-002",
        "department": "TDMS",
        "corridor": "COR-01",
        "description": "OHE contact wire height & stagger adjustment at bridge approach",
        "severity": 3,
        "days_overdue": 3,
        "duration_hours": 3
    },
    {
        "id": "DEF-003",
        "department": "SMMS",
        "corridor": "COR-01",
        "description": "Point machine motor replacement and mechanical stroke check",
        "severity": 5,
        "days_overdue": 8,
        "duration_hours": 2
    },

    # --- Corridor 2: KM 60-65 (Kanpur - Unnao) ---
    {
        "id": "DEF-004",
        "department": "TMS",
        "corridor": "COR-02",
        "description": "USFD flaw detection: urgent thermite rail weld collar renewal",
        "severity": 5,
        "days_overdue": 10,
        "duration_hours": 5
    },
    {
        "id": "DEF-005",
        "department": "TDMS",
        "corridor": "COR-02",
        "description": "Catenary bracket insulator replacement due to flashover pollution",
        "severity": 2,
        "days_overdue": 2,
        "duration_hours": 4
    },

    # --- Corridor 3: KM 85-90 (Prayagraj - Naini) ---
    {
        "id": "DEF-006",
        "department": "TDMS",
        "corridor": "COR-03",
        "description": "OHE tensioning device auto-tension winch servicing & counterweight check",
        "severity": 4,
        "days_overdue": 7,
        "duration_hours": 4
    },
    {
        "id": "DEF-007",
        "department": "SMMS",
        "corridor": "COR-03",
        "description": "Track circuit impedance bond check and digital axle counter testing",
        "severity": 3,
        "days_overdue": 4,
        "duration_hours": 3
    },

    # --- Corridor 4: KM 110-115 (Itarsi - Hoshangabad) ---
    {
        "id": "DEF-008",
        "department": "TMS",
        "corridor": "COR-04",
        "description": "Glued insulated rail joint (GJ) rehabilitation and fishplate tightening",
        "severity": 3,
        "days_overdue": 5,
        "duration_hours": 4
    },
    {
        "id": "DEF-009",
        "department": "SMMS",
        "corridor": "COR-04",
        "description": "Color light signal LED aspect unit replacement & optical alignment",
        "severity": 2,
        "days_overdue": 1,
        "duration_hours": 2
    },
    {
        "id": "DEF-010",
        "department": "TDMS",
        "corridor": "COR-04",
        "description": "Section insulator overhaul and spark erosion runner contact repair",
        "severity": 5,
        "days_overdue": 12,
        "duration_hours": 5
    },

    # --- Corridor 5: KM 130-135 (Nagpur - Wardha) ---
    {
        "id": "DEF-011",
        "department": "TMS",
        "corridor": "COR-05",
        "description": "Switch Expansion Joint (SEJ) gap adjustment for thermal compliance",
        "severity": 4,
        "days_overdue": 4,
        "duration_hours": 3
    },
    {
        "id": "DEF-012",
        "department": "SMMS",
        "corridor": "COR-05",
        "description": "Multi-aspect signalling power cable insulation breakdown test",
        "severity": 3,
        "days_overdue": 2,
        "duration_hours": 2
    }
]
