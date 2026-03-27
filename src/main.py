# main.py
import csv
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import MatplotlibDeprecationWarning
from pathlib import Path

from model import Task
from analysis import (
    perform_rm_analysis,
    check_ll_bound,
    calculate_utilization,
    perform_dm_analysis,
    perform_edf_analysis,
)
from simulation import Scheduler

import warnings
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "results.txt"


# ----------------------------------------------------------------------
# Logging helper (file only, does NOT replace print)
# ----------------------------------------------------------------------
def log_only(*args, sep=" ", end="\n"):
    message = sep.join(str(a) for a in args) + end
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message)


# ----------------------------------------------------------------------
# CSV loader
# ----------------------------------------------------------------------
def load_tasks_from_csv(filename):
    tasks = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                if not row.get('Task'):
                    continue
                name = str(row['Task'])
                tid  = int(name.split("_")[1])
                tasks.append(Task(
                    name=name,
                    id=tid,
                    bcet=int(row.get('BCET', 0)),
                    wcet=int(row['WCET']),
                    period=int(row['Period']),
                    deadline=int(row['Deadline']),
                    priority=int(row.get('Priority', 0)),
                ))
    except FileNotFoundError:
        print("CSV not found. Please check the file path.")
        log_only("CSV not found. Please check the file path.")
    except KeyError as e:
        print(f"CSV parse error: missing column {e}")
        log_only(f"CSV parse error: missing column {e}")
    except ValueError as e:
        print(f"CSV value error: {e}")
        log_only(f"CSV value error: {e}")
    return tasks


# ----------------------------------------------------------------------
# Gantt chart
# ----------------------------------------------------------------------
def plot_gantt(history, tasks, algorithm, duration, prefix=""):
    fig, ax = plt.subplots(figsize=(12, 6))

    colors      = plt.cm.get_cmap('tab10', len(tasks))
    task_colors = {t.id: colors(i) for i, t in enumerate(tasks)}

    merged_blocks = []
    if history:
        current_start = history[0][0]
        current_tid   = history[0][1]

        for t, tid in history:
            if tid != current_tid:
                if current_tid is not None:
                    merged_blocks.append((current_start, t - current_start, current_tid))
                current_tid   = tid
                current_start = t

        if current_tid is not None:
            last_t = history[-1][0] + 1
            merged_blocks.append((current_start, last_t - current_start, current_tid))

    for start, length, tid in merged_blocks:
        ax.broken_barh([(start, length)], (tid * 10, 9), facecolors=task_colors[tid])

    ax.set_ylim(0, max(t.id for t in tasks) * 10 + 10)
    ax.set_xlim(0, duration)
    ax.set_xlabel('Time')
    ax.set_ylabel('Task ID')
    ax.set_yticks([x * 10 + 4.5 for x in [t.id for t in tasks]])
    ax.set_yticklabels([f'T{t.id}' for t in tasks])
    ax.set_title(f'Gantt Chart - {algorithm} Scheduling (Duration: {duration})\n{prefix}')
    ax.grid(True, axis='x')

    out_path = BASE_DIR / 'resultplots' / f'gantt_{algorithm}_{prefix}.png'
    plt.savefig(out_path)
    print(f"Gantt chart saved to {out_path}")
    log_only(f"Gantt chart saved to {out_path}")
    plt.close()


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main(task_file):
    prefix = Path(task_file).stem

    print("Loading task set...")
    log_only("Loading task set...")

    tasks = load_tasks_from_csv(task_file)
    if not tasks:
        print("No tasks loaded. Exiting.")
        log_only("No tasks loaded. Exiting.")
        return

    print("\n" + "=" * 40)
    log_only("\n" + "=" * 40)
    print("          ANALYTICAL RESULTS")
    log_only("          ANALYTICAL RESULTS")
    print("=" * 40)
    log_only("=" * 40)

    u                           = calculate_utilization(tasks)
    is_schedulable, _, ll_bound = check_ll_bound(tasks)

    print(f"Total Utilization U   : {u:.4f}")
    log_only(f"Total Utilization U   : {u:.4f}")
    print(f"Liu & Layland Bound   : {ll_bound:.4f}")
    log_only(f"Liu & Layland Bound   : {ll_bound:.4f}")
    print(f"Schedulable by LL Test: {'Yes' if is_schedulable else 'Inconclusive (Exact Analysis Required)'}")
    log_only(f"Schedulable by LL Test: {'Yes' if is_schedulable else 'Inconclusive (Exact Analysis Required)'}")

    if u > 1:
        print("WARNING: U > 1 — system is overloaded, deadlines will be missed.")
        log_only("WARNING: U > 1 — system is overloaded, deadlines will be missed.")

    rm_analysis    = perform_rm_analysis(tasks)
    df_rm_analytic = pd.DataFrame(rm_analysis).T

    print("\n--- RM Exact WCRT Analysis ---")
    log_only("\n--- RM Exact WCRT Analysis ---")
    print(df_rm_analytic[['Period', 'WCET', 'WCRT_Analytic', 'Schedulable']])
    log_only(df_rm_analytic[['Period', 'WCET', 'WCRT_Analytic', 'Schedulable']].to_string())

    dm_analysis    = perform_dm_analysis(tasks)
    df_dm_analytic = pd.DataFrame(dm_analysis).T

    print("\n--- DM Exact WCRT Analysis ---")
    log_only("\n--- DM Exact WCRT Analysis ---")
    print(df_dm_analytic[['Period', 'Deadline', 'WCET', 'WCRT_Analytic', 'Schedulable']])
    log_only(df_dm_analytic[['Period', 'Deadline', 'WCET', 'WCRT_Analytic', 'Schedulable']].to_string())

    edf_analysis    = perform_edf_analysis(tasks)
    if edf_analysis == False:
        print(task_file)
        log_only(task_file)

    df_edf_analytic = pd.DataFrame(edf_analysis).T

    print("\n--- EDF Exact WCRT Analysis (Hyperperiod Simulation with WCET) ---")
    log_only("\n--- EDF Exact WCRT Analysis (Hyperperiod Simulation with WCET) ---")
    print(df_edf_analytic[['Period', 'Deadline', 'WCET', 'WCRT_Analytic', 'Schedulable']])
    log_only(df_edf_analytic[['Period', 'Deadline', 'WCET', 'WCRT_Analytic', 'Schedulable']].to_string())

    print("\n" + "=" * 40)
    log_only("\n" + "=" * 40)
    print("          SIMULATION RESULTS")
    log_only("          SIMULATION RESULTS")
    print("=" * 40)
    log_only("=" * 40)

    duration = math.lcm(*[t.period for t in tasks]) if tasks else 100
    print(f"Hyperperiod (LCM): {duration}")
    log_only(f"Hyperperiod (LCM): {duration}")

    rm_sim = Scheduler(tasks, algorithm="RM")
    rm_jobs, rm_history = rm_sim.run(duration)
    rm_stats = rm_sim.analyze_results()
    plot_gantt(rm_history, tasks, "RM", duration, prefix)

    edf_sim = Scheduler(tasks, algorithm="EDF")
    edf_jobs, edf_history = edf_sim.run(duration)
    edf_stats = edf_sim.analyze_results()
    plot_gantt(edf_history, tasks, "EDF", duration, prefix)

    dm_sim = Scheduler(tasks, algorithm="DM")
    dm_jobs, dm_history = dm_sim.run(duration)
    dm_stats = dm_sim.analyze_results()
    plot_gantt(dm_history, tasks, "DM", duration, prefix)

    print("\n" + "=" * 40)
    log_only("\n" + "=" * 40)
    print("          COMPARISON REPORT")
    log_only("          COMPARISON REPORT")
    print("=" * 40)
    log_only("=" * 40)

    comparison_data = []
    for t in tasks:
        tid = t.id
        rm_stat  = rm_stats.get(tid, {"Sim_WCRT": -1, "Missed": -1})
        edf_stat = edf_stats.get(tid, {"Sim_WCRT": -1, "Missed": -1})
        dm_stat  = dm_stats.get(tid, {"Sim_WCRT": -1, "Missed": -1})

        comparison_data.append({
            "Task": f"T{tid}",
            "Analytic_WCRT(RM)":  rm_analysis [tid]["WCRT_Analytic"],
            "Analytic_WCRT(DM)":  dm_analysis [tid]["WCRT_Analytic"],
            "Analytic_WCRT(EDF)": edf_analysis[tid]["WCRT_Analytic"],
            "Sim_WCRT(RM)":  rm_stat ["Sim_WCRT"],
            "Sim_WCRT(EDF)": edf_stat["Sim_WCRT"],
            "Sim_WCRT(DM)":  dm_stat ["Sim_WCRT"],
            "RM_Missed":  rm_stat ["Missed"],
            "EDF_Missed": edf_stat["Missed"],
            "DM_Missed":  dm_stat ["Missed"],
        })

    df_comp = pd.DataFrame(comparison_data)

    print(df_comp)
    log_only(df_comp.to_string())

    print("\n--- Validation ---")
    log_only("\n--- Validation ---")

    valid = True
    for _, row in df_comp.iterrows():
        for alg, analytic, sim in [
            ("RM", row["Analytic_WCRT(RM)"], row["Sim_WCRT(RM)"]),
            ("DM", row["Analytic_WCRT(DM)"], row["Sim_WCRT(DM)"]),
            ("EDF", row["Analytic_WCRT(EDF)"], row["Sim_WCRT(EDF)"]),
        ]:
            if analytic != float("inf") and analytic < sim:
                msg = f"DISCREPANCY ({alg}): Task {row['Task']} sim WCRT {sim} > analytic {analytic}"
                print(msg)
                log_only(msg)
                valid = False

    if valid:
        print("Validation passed.")
        log_only("Validation passed.")
    else:
        print("Validation FAILED.")
        log_only("Validation FAILED.")


if __name__ == "__main__":
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    TASKSETS_NS_DIR = BASE_DIR / "tasksets" / "not_schedulable"
    # TASKSETS_S_DIR  = BASE_DIR / "tasksets" / "schedulable"

    # schedulable_files = [
    #     "Full_Utilization_Unique_Periods_taskset.csv",
    #     "High_Utilization_NonUnique_Periods_taskset.csv",
    # ]

    not_schedulable_files = [
        # "Unschedulable_Full_Utilization_NonUnique_Periods_taskset.csv",
        # "Unschedulable_Full_Utilization_Unique_Periods_taskset.csv",
        # "Unschedulable_High_Utilization_NonUnique_Periods_taskset.csv",
        "Unschedulable_High_Utilization_Unique_Periods_taskset.csv",
    ]

    # print("\n" + "=" * 50)
    # log_only("\n" + "=" * 50)
    # print("  SCHEDULABLE TASK SETS")
    # log_only("  SCHEDULABLE TASK SETS")
    # print("=" * 50)
    # log_only("=" * 50)

    # for name in schedulable_files:
    #     f = TASKSETS_S_DIR / name
    #     if f.exists():
    #         print(f"\n>>> {f.name}")
    #         log_only(f"\n>>> {f.name}")
    #         main(f)
    #     else:
    #         print(f"WARNING: File not found: {f}")
    #         log_only(f"WARNING: File not found: {f}")

    print("\n" + "=" * 50)
    log_only("\n" + "=" * 50)
    print("  NOT SCHEDULABLE BY RM (EDF may still schedule)")
    log_only("  NOT SCHEDULABLE BY RM (EDF may still schedule)")
    print("=" * 50)
    log_only("=" * 50)

    for name in not_schedulable_files:
        f = TASKSETS_NS_DIR / name
        if f.exists():
            print(f"\n>>> {f.name}")
            log_only(f"\n>>> {f.name}")
            main(f)
        else:
            print(f"WARNING: File not found: {f}")
            log_only(f"WARNING: File not found: {f}")