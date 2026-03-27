# 02225 Distributed Real-Time Systems — Group 11

This repository contains the work for **02225 Distributed Real-Time Systems** at DTU. It is organized into two mini-projects, each tackling a different aspect of real-time scheduling.

---

## Mini Project 1 — Single-Processor Real-Time Scheduling Analysis

**Location:** [`mini-project-1/`](mini-project-1/)

### Overview

Analyzes periodic real-time task sets on a **single processor** and compares three scheduling algorithms:

| Algorithm | Description |
|-----------|-------------|
| **RM** (Rate Monotonic) | Fixed-priority; higher priority to shorter-period tasks |
| **DM** (Deadline Monotonic) | Fixed-priority; higher priority to shorter-deadline tasks |
| **EDF** (Earliest Deadline First) | Dynamic-priority; always runs the task with the nearest deadline |

For each task set the project produces:
- Exact **WCRT (Worst-Case Response Time)** analysis for RM, DM, and EDF
- Liu & Layland utilization bound check
- Task-set classification (schedulable, RM/DM-unschedulable but EDF-schedulable, or overloaded)
- **Simulation** under both WCET (worst-case) and random (`BCET`–`WCET`) execution times
- Gantt charts (saved to `resultplots/`) and a full text log (`results.txt`)
- Upper-bound validation: simulated WCRT ≤ analytic WCRT for schedulable tasks

### Requirements

- Python 3.10+

```bash
pip install -r mini-project-1/requirements.txt
```

### Run

```bash
cd mini-project-1
python src/main.py
```

This runs all task sets from the `tasksets/` directory and writes results to `results.txt` and `resultplots/`.

### Task Set Categories

| Category | Description |
|----------|-------------|
| Schedulable | Schedulable by RM, DM, and EDF |
| RM/DM-unschedulable | Not schedulable by RM/DM, but schedulable by EDF |
| Overloaded | U > 1; not schedulable by any algorithm on one CPU |

---

## Mini Project 2 — Network Real-Time Scheduling (CBS vs. SP)

**Location:** [`mini-project-2/`](mini-project-2/)

### Overview

Analyzes end-to-end latency of real-time **network streams** using two Traffic Shaping / Scheduling modes:

| Mode | Description |
|------|-------------|
| **CBS** (Credit-Based Shaper) | AVB/TSN credit-based traffic shaping (IEEE 802.1Qav) |
| **SP** (Strict Priority) | Classic strict-priority queuing |

For each test case the project:
- Loads a network **topology**, **streams**, and **routes** from JSON files
- Runs a **simulation** for both CBS and SP modes
- Computes **analytical WCRT** for both modes
- Compares simulated vs. analytical worst-case end-to-end latency per stream
- Saves results to a CSV file inside the test case folder

### Requirements

- Python 3.10+

```bash
pip install -r mini-project-2/requirements.txt
```

### Run

```bash
cd mini-project-2
python -m src.main <case_id>
```

`case_id` selects the test case:

| Case | Type |
|------|------|
| 1–3 | Normal cases |
| 4 | Starvation case |

Example:

```bash
python -m src.main 1
```

### Output

- Console table: `Stream ID`, `PCP`, `Sim(CBS)`, `Sim(SP)`, `Ana(CBS)`, `Ana(SP)` (latencies in µs)
- CSV file: `testcases/test_case_<id>/Case-<id>-WCRTs_Comparison.csv`
- Pre-computed results are stored in the `results/` folder

---

## Repository Structure

```
.
├── mini-project-1/          # Single-processor scheduling analysis
│   ├── src/                 # Analysis, simulation, and main script
│   ├── tasksets/            # CSV task set definitions
│   ├── resultplots/         # Generated Gantt charts and plots
│   ├── results.txt          # Full console output log
│   └── requirements.txt
│
└── mini-project-2/          # Network scheduling (CBS vs. SP)
    ├── src/                 # Loader, model, scheduler, simulation, analysis
    ├── testcases/           # JSON topology/streams/routes per test case
    ├── results/             # Pre-computed CSV results
    └── requirements.txt
```