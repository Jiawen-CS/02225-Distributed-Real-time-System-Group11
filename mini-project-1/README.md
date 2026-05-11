# 02225 DRTS Mini Project 1

This project analyzes periodic real-time task sets on a single processor and compares:

- Rate Monotonic / Deadline Monotonic exact WCRT analysis
- EDF exact WCRT analysis for synchronous periodic task sets
- Simulated response times under WCET execution
- Simulated response times under random execution times in `[BCET, WCET]`

The implementation is located in [src/main.py](/Users/powerbear/Documents/dtu/02225%20Distributed%20real-time%20/02225-Distributed-Real-time-System-Group11-master/src/main.py).

## Requirements

- Python 3.10+
- Install dependencies from the project root:

```bash
pip install -r requirements.txt
```

## Run the analytical

From the project root:

```bash
python -m src.main
```

This runs the selected schedulable, RM/DM-unschedulable, and overloaded task sets from the `tasksets/` directory.

If you want to run custom test sets, then change the variable TASKSETS_NS_DIR for custom unschedulable task sets,
or TASKSETS_S_DIR for custom schedulable task sets. The custom task sets lie within the sub-directories.

### Output

The program prints:

- analytical WCRT results for RM, DM, and EDF
- task-set classification
- simulation results for WCET and random execution
- comparison tables between analytic and simulated response times
- upper-bound validation for analytically schedulable tasks

Generated files:

- plots are saved in `resultplots/`
- console output is also saved to `logs/results.txt`

### Notes

- For very large hyperperiods, Gantt chart generation is skipped automatically to avoid excessive runtime and memory use.
- `Validation passed` means the simulated WCET response time did not exceed the analytic bound for tasks that were analytically schedulable. Unschedulable or infinite-WCRT cases are reported separately and skipped from that upper-bound check.

## Choosing a reasonable number of hyper-periods for simulation

We have chosen some tasks for simulation. We first simulate all the chosen task sets such that we observe
there is no new WCRT observed for each task set, then choosing the maximum one.

Run 
```bash
python -m src.pick_hyperiod
```

- plots are saved in `resultplots_customTest/`
- console output is also saved to `logs/pick_hyperiod_results.txt`

## Simulation
To do simulation, you run:
```bash
python -m src.taskset_simulation
```

The simulation contains five simulations mode:
1. Deterministic WCET.
2. Deterministic BCET.
3. Uniformly random execution time.
4. BCET-biased execution time.
5. WCET-biased execution time.

All results will be log into logs/simulation.txt. Moreover, the code will saves the Gantt chart and the running time
distribution of each job of each task within a task set, according to each schedulers.