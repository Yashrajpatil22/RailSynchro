# RailSynchro — AI-Powered Automatic Block Planning MVP (SIH26027)

> **Smart India Hackathon Problem Statement SIH26027**  
> *AI-Powered Automatic Block Planning to Maximize Asset Availability for Train Operations on Indian Railways*

---

## 1. Overview & Operational Problem

In Indian Railways, infrastructure maintenance is planned independently across three separate departmental silos:
- **TMS** (*Track Management System*): Permanent Way (P-Way) civil maintenance, rail flaw replacement, ballast tamping, turnout overhauls.
- **TDMS** (*Traction Distribution Management System*): Overhead Equipment (OHE) 25kV catenary maintenance, insulator replacements, neutral section checks.
- **SMMS** (*Signalling & Telecommunication Maintenance Management System*): Point machines, digital axle counters, track circuits, signal aspect testing.

A fourth system, **COA** (*Control Office Application*), controls train timetables, passenger express paths, and freight convoys.

### The Problem
When each department requests track blocks (temporary track closures) independently without coordination:
1. **Excessive Track Downtime**: Separate closures are requested on the same corridor on different days or hours, multiplying downtime.
2. **Timetable Disruptions**: Manual coordination often results in block cancellations or conflicts with high-priority passenger trains.
3. **Punctuality Loss**: Repeated speed restrictions and disjointed blocks severely degrade sectional throughput.

### The RailSynchro Solution
RailSynchro provides a centralized constraint-optimization engine powered by **Google OR-Tools CP-SAT**:
- **Consolidates Overlapping Requests**: Merges multiple departmental requests on the same corridor into **one single joint closure window** whose duration equals the $\max(\text{durations})$ of the merged jobs.
- **Strict COA Timetable Clearance**: Guarantees zero overlap with scheduled passenger or freight passage hours.
- **Division Concurrency Limits**: Enforces a global divisional capacity limit ($\le 2$ concurrent blocks across the division) reflecting traction power isolation and safety supervisor limits.
- **Urgency-Weighted Dispatch**: Schedules high-urgency corridors earlier in the 7-day horizon based on transparent, auditable defect scoring.

---

## 2. Mathematical Formulation & Solver Engine

### A. Explainable Rule-Based Defect Prioritization
In safety-critical railway engineering under **RDSO** and **Commissioner of Railway Safety (CRS)** regulations, decisions must be 100% deterministic and auditable. RailSynchro uses an explicit rule-based weighted formula rather than an opaque or unverified machine learning model:

$$\text{Raw Score} = (\text{Severity} \times 12.0) + (\min(\text{Days Overdue}, 14) \times 2.5) + (\text{Safety Boost})$$

where $\text{Safety Boost} = 10.0$ if $\text{Severity} \ge 4$, else $0.0$. The final score is normalized to $[5.0, 100.0]$.

> **Architectural Note**: This transparent rule-based design guarantees full auditability for Chief Controllers. When historical outcome logs (cleared defect records, speed restriction durations, incident ground truth) become available in production, the formula can seamlessly ingest a trained gradient-boosted regression model (e.g. LightGBM).

### B. Google OR-Tools CP-SAT Constraint Model
- **Set of Corridors**: $C = \{c_1, c_2, \dots, c_m\}$
- **Defects per Corridor**: $D_c = \{d \in \text{Defects} \mid d.\text{corridor} = c\}$
- **Joint Window Duration**: $W_c = \max_{d \in D_c} (d.\text{duration\_hours})$
- **Corridor Urgency**: $U_c = \sum_{d \in D_c} d.\text{risk\_score}$
- **Feasible Start Hours**:
  $$F_c = \left\{ t \in [0, 168 - W_c] \;\middle|\; \forall h \in [t, t + W_c - 1],\; h \notin \text{COA\_Occupied}_c \right\}$$
- **Decision Variables**:
  - $\text{Start}_c \in F_c$ (start hour of the joint block)
  - $\text{End}_c = \text{Start}_c + W_c$
  - $\text{Interval}_c = \text{NewIntervalVar}(\text{Start}_c, W_c, \text{End}_c)$
- **Global Concurrency Constraint (Divisional Capacity)**:
  $$\text{Cumulative}(\{\text{Interval}_c\}, \text{demands}=\{1\}, \text{capacity}=2)$$
  Ensures no more than 2 corridors undergo maintenance simultaneously across the division.
- **Objective Function**:
  $$\min \sum_{c \in C} \text{round}(U_c \times 10) \cdot \text{Start}_c$$
  Minimizes the urgency-weighted start times, ensuring that high-urgency corridors are resolved in the earliest feasible train-free windows.

---

## 3. Verified Numerical Comparison (Before vs After)

| Metric | Baseline ("Before" — Siloed) | RailSynchro ("After" — Joint Optimization) | Impact |
|---|---|---|---|
| **Total Track Downtime** | **41 hours** | **21 hours** | **▼ 48.8% reduction** |
| **Track Closures Required** | **12 separate blocks** | **5 joint windows** | **▼ 58.3% fewer interruptions** |
| **COA Passenger Conflicts** | 0 | 0 | **100% timetable clearance** |
| **Solver Status** | N/A (Manual) | **OPTIMAL** (OR-Tools CP-SAT) | **Solved in ~16 ms** |

---

## 4. Running Locally

### Step 1: Backend Setup
```bash
# Navigate to backend directory
cd backend

# (Optional) Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- Full App & Web Console: [http://localhost:8000](http://localhost:8000) (FastAPI directly serves the frontend dashboard!)
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Defects Endpoint: [http://localhost:8000/api/defects](http://localhost:8000/api/defects)
- Schedule Endpoint: [http://localhost:8000/api/schedule](http://localhost:8000/api/schedule)

### Step 2: Accessing the Dashboard
You have two effortless options (both require **zero user input**):

- **Option A (Recommended — Unified Server)**:  
  Just navigate to [http://localhost:8000](http://localhost:8000) in your browser. The FastAPI server hosts both the REST API and the railway control dashboard together!
  
- **Option B (Standalone Frontend)**:  
  Open `frontend/index.html` directly in your browser (or serve via `cd frontend && python -m http.server 3000`). The dashboard automatically detects `localhost` and connects to `http://localhost:8000` without asking you to type anything!

Click **⚡ Run Optimization** to initiate the live CP-SAT optimization.

---

## 5. Deployment Guide

### A. Deploy Backend to Render (Python Web Service)
1. Push this repository to GitHub or GitLab.
2. Log in to [Render.com](https://render.com) and click **New +** $\rightarrow$ **Web Service**.
3. Select your repository.
4. Configure service settings:
   - **Name**: `railsynchro-backend`
   - **Environment**: `Python 3`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Click **Create Web Service**.
6. Once deployed, note your Render service URL (e.g. `https://railsynchro-backend.onrender.com`).
   *Note: Render serves both the API endpoints and the frontend dashboard automatically at this URL!*

### B. Deploy Standalone Frontend to Vercel (Optional)
If you prefer hosting the frontend as an independent static site on Vercel:
1. In `frontend/config.js`, set `PROD_API_URL` to your Render service URL:
   ```javascript
   window.RAILSYNCHRO_CONFIG = {
     PROD_API_URL: "https://your-backend-name.onrender.com",
     LOCAL_API_URL: "http://localhost:8000",
     API_URL_OVERRIDE: ""
   };
   ```
2. Log in to [Vercel.com](https://vercel.com) and click **Add New** $\rightarrow$ **Project**.
3. Select your repository and set **Root Directory** to `frontend`.
4. Click **Deploy**.
5. When opened on Vercel, RailSynchro automatically detects the cloud environment and connects directly to your Render backend with zero user intervention!

---

## 6. Project Directory Structure
```
RailSynchro/
├── backend/
│   ├── data.py             # 5 Corridors, 168h COA timetable, 12 sample defects
│   ├── scoring.py          # Explainable rule-based risk scoring formula
│   ├── solver.py           # Google OR-Tools CP-SAT solver & siloed baseline
│   ├── main.py             # FastAPI app (serves /api routes and static frontend)
│   ├── verify_schedule.py  # Local verification script
│   └── requirements.txt    # Python dependencies (fastapi, uvicorn, ortools)
├── frontend/
│   ├── config.js           # Environment configuration (Local vs Cloud Backend URL)
│   └── index.html          # Industrial railway operations control console UI
└── README.md               # Comprehensive architecture and deployment guide
```
