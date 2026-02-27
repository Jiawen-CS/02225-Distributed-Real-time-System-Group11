# Mini Project 1: Uniprocessor Real-Time Scheduling

**Course:** 02225 Distributed Real-Time Systems  
**Group:** 11  
**Reference:** Buttazzo, G. C. "Hard Real-Time Computing Systems" (3rd Edition)

---

## 📋 Project Overview

This project implements a complete real-time scheduling analysis and simulation framework for **uniprocessor systems** with **constrained deadlines** ($D_i \leq T_i$).

### Implemented Features

| Step | Component | Description |
|------|-----------|-------------|
| **1** | Task Model | Task dataclass with UUniFast generator (12 tasks) |
| **2** | Analysis Engine | DM (RTA) and EDF (PDC) schedulability analysis |
| **3** | Simulator | Discrete-time tick-by-tick simulation |
| **4** | Visualization | Publication-quality charts (WCRT, Preemptions, Gantt) |

### Supported Scheduling Algorithms

- **RM** (Rate Monotonic): Static priority by period
- **DM** (Deadline Monotonic): Static priority by relative deadline  
- **EDF** (Earliest Deadline First): Dynamic priority by absolute deadline

---

## 🚀 Quick Start

### Prerequisites

```bash
# From repository root
pip install -r requirements.txt
```

### Run Complete Analysis & Visualization

```bash
cd mini_project_1/src
python visualizer.py
```

This will:
1. Generate task sets with Low (U≈0.5) and High (U≈0.9) utilization (12 tasks each)
2. Run analytical schedulability tests (RTA for DM, PDC for EDF)
3. Simulate scheduling with random execution times [BCET, WCET]
4. Generate 5 publication-quality charts in `resultplots/`

### Run Individual Components

```bash
cd mini_project_1/src

# Step 1: Task Model & Generation
python model.py

# Step 2: Analytical Schedulability Analysis
python analysis.py

# Step 3: Discrete-Time Simulation
python simulation.py

# Step 4: Visualization (all charts)
python visualizer.py
```

---

## 📁 Project Structure

```
mini_project_1/
├── README.md
├── src/
│   ├── __init__.py
│   ├── model.py          # Step 1: Task model & UUniFast generator
│   ├── analysis.py       # Step 2: DM (RTA) & EDF (PDC) analysis
│   ├── simulation.py     # Step 3: Discrete-time simulator
│   ├── visualizer.py     # Step 4: Chart generation
│   └── main.py           # Legacy entry point (CSV-based)
├── resultplots/          # Generated charts
│   ├── wcrt_comparison.png
│   ├── preemption_comparison.png
│   ├── gantt_RM.png
│   ├── gantt_DM.png
│   └── gantt_EDF.png
└── tasksets/             # Sample CSV task sets
    ├── schedulable/
    └── not_schedulable/
```

---

## 📊 Output Charts

### 1. WCRT Comparison (`wcrt_comparison.png`)
Grouped bar chart comparing **Theoretical WCRT** vs **Simulated Max Response Time** for DM scheduling under high utilization. Shows deadline lines to identify missed deadlines.

### 2. Preemption Comparison (`preemption_comparison.png`)
Bar chart comparing **DM vs EDF preemptions** across utilization levels.  
**Key Finding:** EDF has FEWER preemptions than DM (confirms Buttazzo's "Judgment Day" paper).

### 3-5. Gantt Charts (`gantt_RM.png`, `gantt_DM.png`, `gantt_EDF.png`)
Timeline visualization showing task execution over the first 600 time units for all 12 tasks.

---

## 🔬 Technical Details

### Task Model (Buttazzo Notation)

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| Period | $T_i$ | Inter-arrival time |
| Relative Deadline | $D_i$ | Time from release to deadline |
| WCET | $C_i$ | Worst-Case Execution Time |
| BCET | $BCET_i$ | Best-Case Execution Time |
| Phase | $\Phi_i$ | Initial release offset |

**Constraint:** $D_i \leq T_i$ (constrained deadline model)

### UUniFast Algorithm

Task set generation uses the **UUniFast algorithm** (Bini & Buttazzo, 2005) for unbiased utilization distribution:

```python
from model import generate_task_sets_by_utilization

low_u_tasks, high_u_tasks = generate_task_sets_by_utilization(
    n_tasks=12,
    seed=42
)
# Returns: Low U ≈ 0.5, High U ≈ 0.9
```

### DM Analysis (Response Time Analysis)

Iterative fixed-point algorithm:
$$R_i^{(s)} = C_i + \sum_{h \in hp(i)} \left\lceil \frac{R_i^{(s-1)}}{T_h} \right\rceil C_h$$

Task is schedulable if $R_i \leq D_i$.

### EDF Analysis (Processor Demand Criterion)

For constrained deadlines:
$$\forall L \in [0, L^*]: \sum_{i=1}^{n} \left\lfloor \frac{L + T_i - D_i}{T_i} \right\rfloor C_i \leq L$$

Where $L^* = \max(D_{max}, \frac{\sum C_i(T_i - D_i)}{1 - U})$

---

## 📈 Example Output

```
================================================================================
 DRTS Mini-Project Step 4: Visualization
================================================================================

▶ Step 1: Generating task sets...
  Low U task set:  U = 0.5773
  High U task set: U = 1.0496

▶ Step 2: Running analytical analysis...
  Low U:  DM=True, EDF=True
  High U: DM=False, EDF=False

▶ Step 3: Running simulations...
  Low U DM:  Preemptions=1843, Misses=0
  Low U EDF: Preemptions=1732, Misses=0
  High U DM:  Preemptions=4972, Misses=18
  High U EDF: Preemptions=4307, Misses=0
  High U RM:  Preemptions=4809, Misses=10

▶ Step 4: Generating visualization charts...
  ✓ Saved: wcrt_comparison.png
  ✓ Saved: preemption_comparison.png
  ✓ Saved: gantt_RM.png
  ✓ Saved: gantt_DM.png
  ✓ Saved: gantt_EDF.png

Key Findings:
  • DM failed for τ_0 in high U (WCRT > D)
  • EDF has FEWER preemptions than DM (Judgment Day confirmed)
================================================================================
```

---

## 📚 References

1. Buttazzo, G. C. (2011). *Hard Real-Time Computing Systems: Predictable Scheduling Algorithms and Applications* (3rd ed.). Springer.

2. Buttazzo, G. C. (2005). Rate Monotonic vs. EDF: Judgment Day. *Real-Time Systems*, 29(1), 5-26.

3. Bini, E., & Buttazzo, G. C. (2005). Measuring the Performance of Schedulability Tests. *Real-Time Systems*, 30(1-2), 129-154.
