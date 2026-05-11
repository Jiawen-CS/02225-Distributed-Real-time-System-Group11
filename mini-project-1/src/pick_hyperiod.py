import csv
import math
import os

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import MatplotlibDeprecationWarning
from pathlib import Path
from utils import print_and_log, log_only
import warnings

from model import Task
from simulation import Scheduler

warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "results.txt"
PLOTS_DIR = BASE_DIR / "resultplots_customTest"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_HISTORY_FOR_PLOTS = 200_000



# ----------------------------------------------------------------------
# CSV loader
# ----------------------------------------------------------------------
def load_tasks_from_csv(filename):
    tasks = []
    try:
        with open(filename, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, skipinitialspace=True)

            for row in reader:
                if not row.get("Task"):
                    continue

                name = str(row["Task"])
                tid = int(name.split("_")[1])

                bcet_val = row.get("BCET", "")
                priority_val = row.get("Priority", "")

                tasks.append(Task(
                    name=name,
                    id=tid,
                    bcet=int(bcet_val) if str(bcet_val).strip() != "" else int(row["WCET"]),
                    wcet=int(row["WCET"]),
                    period=int(row["Period"]),
                    deadline=int(row["Deadline"]),
                    priority=int(priority_val) if str(priority_val).strip() != "" else 0,
                ))

    except FileNotFoundError:
        print_and_log(f"CSV not found: {filename}")
    except KeyError as e:
        print_and_log(f"CSV parse error: missing column {e}")
    except ValueError as e:
        print_and_log(f"CSV value error in {filename}: {e}")

    return tasks

# ----------------------------------------------------------------------
# One task set
# ----------------------------------------------------------------------
def main(task_file):
    prefix = Path(task_file).stem

    print_and_log(f"\n>>> {prefix}")
    print_and_log("Loading task set...")

    tasks = load_tasks_from_csv(task_file)
    if not tasks:
        print_and_log("No tasks loaded. Exiting.")
        return

    # Random simulation: for BCET~WCET runtime behavior
    max_wcrt = -1
    print("=" * 40)
    print('RANDOM SIMULATION MODE ACTIVATED')
    print("=" * 40)
    rm_sim_rand = Scheduler(tasks, algorithm="RM", execution_mode="random_uniform", seed=42)
    _, observed_wcrt = rm_sim_rand.run_until_wcrt_converges()
    if (observed_wcrt > max_wcrt):
        max_wcrt = observed_wcrt

    edf_sim_rand = Scheduler(tasks, algorithm="EDF", execution_mode="random_uniform", seed=42)
    _, observed_wcrt = edf_sim_rand.run_until_wcrt_converges()
    if (observed_wcrt > max_wcrt):
        max_wcrt = observed_wcrt

    dm_sim_rand = Scheduler(tasks, algorithm="DM", execution_mode="random_uniform", seed=42)
    _, observed_wcrt = dm_sim_rand.run_until_wcrt_converges()
    if (observed_wcrt > max_wcrt):
        max_wcrt = observed_wcrt

    return max_wcrt


# ----------------------------------------------------------------------
# Batch runner
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    TASKSETS_S_DIR = BASE_DIR / "tasksets" / "simulation_tasksets"

    schedulable_files = [
        f for f in os.listdir(TASKSETS_S_DIR)
        if os.path.isfile(os.path.join(TASKSETS_S_DIR, f))
    ]

    print_and_log("\n" + "=" * 60)
    print_and_log("=" * 60)
    max_wcrt = -1
    for name in schedulable_files:
        f = TASKSETS_S_DIR / name
        if f.exists():
            observed_wcrt = main(f)
            if (observed_wcrt > max_wcrt):
                max_wcrt = observed_wcrt
        else:
            print_and_log(f"WARNING: File not found: {f}")

    print(f"Maximum number of hyperperiods are: {max_wcrt}")