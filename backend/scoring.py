"""
RailSynchro Scoring Module: Transparent, Explainable Rule-Based Defect Prioritization
====================================================================================
Problem Statement: SIH26027 (Automatic Block Planning for Indian Railways)

DESIGN RATIONALE & ARCHITECTURAL NOTE:
--------------------------------------
In high-consequence railway systems (under RDSO and Commissioner of Railway Safety
regulations), scheduling and asset intervention decisions must be 100% deterministic,
auditable, and explainable to Chief Controllers and Permanent Way Engineers.

We intentionally use a transparent, explainable RULE-BASED weighted priority formula
rather than an unverified machine learning model (such as LightGBM or XGBoost).
Claiming a trained ML model at this prototype stage would be technically unsound because:
  1. Real historical maintenance outcome data (e.g. deferred block derailment incidents,
     asset failure records post-maintenance delay) is not available in public SIH problem data.
  2. Training an ML model on synthetic labels simply hardcodes the generator's biases
     while hiding them inside an opaque model.
  3. Safety-critical railway operations demand clear mathematical audit trails where an
     engineer can inspect exactly why a track flaw was prioritized over catenary wire adjustment.

UPGRADE PATH:
When Indian Railways deploys RailSynchro in a division and accumulates historical logs
(TMS defect clearing times, COA train punctuality impact, and failure records), this module
can readily ingest a trained gradient-boosted regression model (e.g. LightGBM) to refine
the weight parameters.
"""

from typing import Dict, Any

def compute_defect_risk_score(defect: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a deterministic, explainable risk score (scale 0-100) based on:
      - severity (1 to 5): physical criticality of the defect
      - days_overdue: operational delay beyond standard inspection schedule
      - critical_boost: extra urgency for high-severity track/OHE flaws (severity >= 4)
    
    Formula:
      severity_pts  = severity * 12.0               (range: 12.0 - 60.0)
      overdue_pts   = min(days_overdue, 14) * 2.5    (range: 0.0 - 35.0)
      safety_boost  = 10.0 if severity >= 4 else 0.0 (range: 0.0 or 10.0)
      raw_score     = severity_pts + overdue_pts + safety_boost
      risk_score    = min(100.0, max(5.0, raw_score))
    """
    severity = defect.get("severity", 3)
    days_overdue = defect.get("days_overdue", 0)
    
    # 1. Base Severity component (weight = 12.0 per level)
    severity_pts = float(severity * 12.0)
    
    # 2. Days Overdue component (capped at 14 days to avoid skewing)
    effective_overdue = min(days_overdue, 14)
    overdue_pts = float(effective_overdue * 2.5)
    
    # 3. Safety critical boost for major fractures or high-voltage OHE hazards
    safety_boost = 10.0 if severity >= 4 else 0.0
    
    raw_score = severity_pts + overdue_pts + safety_boost
    risk_score = round(min(100.0, max(5.0, raw_score)), 1)
    
    # Categorical Priority Level
    if risk_score >= 75.0:
        priority_level = "CRITICAL"
        priority_color = "#ef4444"  # Red
    elif risk_score >= 55.0:
        priority_level = "HIGH"
        priority_color = "#f59e0b"  # Amber
    elif risk_score >= 35.0:
        priority_level = "MEDIUM"
        priority_color = "#3b82f6"  # Blue
    else:
        priority_level = "LOW"
        priority_color = "#10b981"  # Green
        
    explanation = (
        f"Severity {severity}/5 yields {severity_pts:.0f} pts; "
        f"{days_overdue} days overdue yields {overdue_pts:.1f} pts; "
        f"{'Safety boost: +10 pts' if safety_boost > 0 else 'No safety boost'}."
    )
    
    return {
        "risk_score": risk_score,
        "priority_level": priority_level,
        "priority_color": priority_color,
        "breakdown": {
            "severity_pts": severity_pts,
            "overdue_pts": overdue_pts,
            "safety_boost": safety_boost,
            "explanation": explanation
        }
    }
