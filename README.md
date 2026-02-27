# 02225 Distributed Real-Time Systems - Group 11

**Course:** 02225 Distributed Real-Time Systems (DTU)  
**Group:** 11  
**Semester:** Spring 2026

---

## 📋 Repository Overview

This repository contains all mini projects for the 02225 Distributed Real-Time Systems course.

| Project | Topic | Status |
|---------|-------|--------|
| [Mini Project 1](mini_project_1/) | Uniprocessor Real-Time Scheduling | ✅ Complete |
| [Mini Project 2](mini_project_2/) | TBD | 🔄 Pending |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.12
pip install -r requirements.txt
```

### Run Mini Project 1

```bash
cd mini_project_1/src
python visualizer.py
```

### Run Mini Project 2

```bash
cd mini_project_2/src
# Instructions will be added when implemented
```

---

## 📁 Repository Structure

```
02225-Distributed-Real-time-System-Group11/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .gitignore
│
├── mini_project_1/           # Uniprocessor Real-Time Scheduling
│   ├── README.md             # Detailed documentation
│   ├── src/
│   │   ├── model.py          # Task model & UUniFast generator
│   │   ├── analysis.py       # DM (RTA) & EDF (PDC) analysis
│   │   ├── simulation.py     # Discrete-time simulator
│   │   ├── visualizer.py     # Chart generation
│   │   └── main.py           # Legacy CSV-based entry point
│   ├── tasksets/             # Sample CSV task sets
│   └── resultplots/          # Generated charts
│
└── mini_project_2/           # [To Be Implemented]
    ├── README.md
    └── src/
```

---

## 📊 Mini Project 1 Highlights

### Implemented Features
- **Task Model**: Buttazzo notation ($T_i$, $D_i$, $C_i$, BCET, $\Phi_i$)
- **UUniFast Algorithm**: Unbiased task set generation (Bini & Buttazzo, 2005)
- **Schedulability Analysis**: 
  - DM: Response Time Analysis (RTA)
  - EDF: Processor Demand Criterion (PDC)
- **Discrete-Time Simulation**: Random execution times [BCET, WCET]
- **Visualization**: WCRT comparison, Preemption comparison, Gantt charts

### Key Findings
- **EDF has FEWER preemptions than DM** (confirms Buttazzo's "Judgment Day" paper)
- DM is optimal among fixed-priority for constrained deadlines
- Simulation results match theoretical predictions

### Output Charts
| Chart | Description |
|-------|-------------|
| `wcrt_comparison.png` | Theory vs Simulation WCRT |
| `preemption_comparison.png` | DM vs EDF preemption counts |
| `gantt_RM.png` | Rate Monotonic schedule |
| `gantt_DM.png` | Deadline Monotonic schedule |
| `gantt_EDF.png` | Earliest Deadline First schedule |

---

## 📚 References

1. Buttazzo, G. C. (2011). *Hard Real-Time Computing Systems* (3rd ed.). Springer.
2. Buttazzo, G. C. (2005). Rate Monotonic vs. EDF: Judgment Day. *Real-Time Systems*.
3. Bini, E., & Buttazzo, G. C. (2005). Measuring the Performance of Schedulability Tests.

---

## 📝 License

This project is developed for educational purposes as part of DTU course 02225.
