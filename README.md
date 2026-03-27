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

## Run

From the project root:

```bash
python src/main.py
```

This runs the selected schedulable, RM/DM-unschedulable, and overloaded task sets from the `tasksets/` directory.

## Output

The program prints:

- analytical WCRT results for RM, DM, and EDF
- task-set classification
- simulation results for WCET and random execution
- comparison tables between analytic and simulated response times
- upper-bound validation for analytically schedulable tasks

Generated files:

- plots are saved in `resultplots/`
- console output is also saved to `results.txt`

## Notes

- For very large hyperperiods, Gantt chart generation is skipped automatically to avoid excessive runtime and memory use.
- Random simulations do not store full execution histories, which keeps large task sets practical to run.
- `Validation passed` means the simulated WCET response time did not exceed the analytic bound for tasks that were analytically schedulable. Unschedulable or infinite-WCRT cases are reported separately and skipped from that upper-bound check.
