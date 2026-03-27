import csv
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import MatplotlibDeprecationWarning
from pathlib import Path
import warnings

from model import Task
from analysis import (
    perform_rm_analysis,
    perform_dm_analysis,
    perform_edf_analysis,
    calculate_utilization,
    check_ll_bound,
)
from simulation import Scheduler

warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "results.txt"
PLOTS_DIR = BASE_DIR / "resultplots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_HISTORY_FOR_PLOTS = 200_000


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def log_only(*args, sep=" ", end="\n"):
    message = sep.join(str(a) for a in args) + end
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message)


def print_and_log(text=""):
    print(text)
    log_only(text)


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
# Gantt chart
# ----------------------------------------------------------------------
def plot_gantt(history, tasks, algorithm, duration, prefix="", mode="wcet"):
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = plt.cm.get_cmap("tab10", len(tasks))
    task_colors = {t.id: colors(i) for i, t in enumerate(tasks)}

    merged_blocks = []
    if history:
        current_start = history[0][0]
        current_tid = history[0][1]

        for t, tid in history:
            if tid != current_tid:
                if current_tid is not None:
                    merged_blocks.append((current_start, t - current_start, current_tid))
                current_tid = tid
                current_start = t

        if current_tid is not None:
            last_t = history[-1][0] + 1
            merged_blocks.append((current_start, last_t - current_start, current_tid))

    for start, length, tid in merged_blocks:
        ax.broken_barh([(start, length)], (tid * 10, 9), facecolors=task_colors[tid])

    ax.set_ylim(0, max(t.id for t in tasks) * 10 + 10)
    ax.set_xlim(0, duration)
    ax.set_xlabel("Time")
    ax.set_ylabel("Task ID")
    ax.set_yticks([x * 10 + 4.5 for x in [t.id for t in tasks]])
    ax.set_yticklabels([f"T{t.id}" for t in tasks])
    ax.set_title(f"Gantt Chart - {algorithm} ({mode}) - {prefix}")
    ax.grid(True, axis="x")

    out_path = PLOTS_DIR / f"gantt_{algorithm}_{mode}_{prefix}.png"
    plt.savefig(out_path)
    plt.close()

    print_and_log(f"Gantt chart saved to {out_path}")


# ----------------------------------------------------------------------
# Classification
# ----------------------------------------------------------------------
def classify_taskset(u, rm_analysis, dm_analysis, edf_analysis):
    rm_ok = all(v["Schedulable"] for v in rm_analysis.values())
    dm_ok = all(v["Schedulable"] for v in dm_analysis.values())
    edf_ok = all(v["Schedulable"] for v in edf_analysis.values())

    if rm_ok and dm_ok and edf_ok:
        return "Schedulable by RM/DM and EDF"

    if (not rm_ok or not dm_ok) and edf_ok:
        return "Not schedulable by RM/DM, but schedulable by EDF"

    if u > 1:
        return "Overloaded: not schedulable on one CPU"

    return "Not schedulable under fixed-priority; EDF also fails"


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

    # --------------------------------------------------------------
    # Analytical results
    # --------------------------------------------------------------
    print_and_log("\n" + "=" * 40)
    print_and_log("          ANALYTICAL RESULTS")
    print_and_log("=" * 40)

    u = calculate_utilization(tasks)
    ll_ok, _, ll_bound = check_ll_bound(tasks)

    print_and_log(f"Total Utilization U   : {u:.4f}")
    print_and_log(f"Liu & Layland Bound   : {ll_bound:.4f}")
    print_and_log(
        f"Schedulable by LL Test: {'Yes' if ll_ok else 'Inconclusive (Exact Analysis Required)'}"
    )

    if u > 1:
        print_and_log("WARNING: U > 1 — overloaded system; no algorithm can schedule all jobs on one CPU.")

    rm_analysis = perform_rm_analysis(tasks)
    dm_analysis = perform_dm_analysis(tasks)
    edf_analysis = perform_edf_analysis(tasks)

    df_rm = pd.DataFrame(rm_analysis).T
    df_dm = pd.DataFrame(dm_analysis).T
    df_edf = pd.DataFrame(edf_analysis).T

    print_and_log("\n--- RM Exact WCRT Analysis ---")
    print(df_rm[["Period", "Deadline", "WCET", "WCRT_Analytic", "Schedulable"]])
    log_only(df_rm[["Period", "Deadline", "WCET", "WCRT_Analytic", "Schedulable"]].to_string())

    print_and_log("\n--- DM Exact WCRT Analysis ---")
    print(df_dm[["Period", "Deadline", "WCET", "WCRT_Analytic", "Schedulable"]])
    log_only(df_dm[["Period", "Deadline", "WCET", "WCRT_Analytic", "Schedulable"]].to_string())

    print_and_log("\n--- EDF Exact WCRT Analysis (Appendix-based hyperperiod schedule with WCET) ---")
    print(df_edf[["Period", "Deadline", "WCET", "WCRT_Analytic", "Schedulable"]])
    log_only(df_edf[["Period", "Deadline", "WCET", "WCRT_Analytic", "Schedulable"]].to_string())

    classification = classify_taskset(u, rm_analysis, dm_analysis, edf_analysis)
    print_and_log(f"\nTask-set classification: {classification}")

    # --------------------------------------------------------------
    # Simulation results
    # --------------------------------------------------------------
    print_and_log("\n" + "=" * 40)
    print_and_log("          SIMULATION RESULTS")
    print_and_log("=" * 40)

    duration = math.lcm(*[t.period for t in tasks]) if tasks else 100
    print_and_log(f"Hyperperiod (LCM): {duration}")
    should_plot = duration <= MAX_HISTORY_FOR_PLOTS
    if not should_plot:
        print_and_log(
            f"Skipping Gantt chart generation because hyperperiod {duration} "
            f"exceeds plot threshold {MAX_HISTORY_FOR_PLOTS}."
        )

    # WCET simulation: for validating analytic bounds
    rm_sim_wcet = Scheduler(tasks, algorithm="RM", execution_mode="wcet", seed=42)
    _, rm_hist_wcet = rm_sim_wcet.run(duration, record_history=should_plot)
    rm_stats_wcet = rm_sim_wcet.analyze_results()
    if should_plot:
        plot_gantt(rm_hist_wcet, tasks, "RM", duration, prefix=prefix, mode="wcet")

    edf_sim_wcet = Scheduler(tasks, algorithm="EDF", execution_mode="wcet", seed=42)
    _, edf_hist_wcet = edf_sim_wcet.run(duration, record_history=should_plot)
    edf_stats_wcet = edf_sim_wcet.analyze_results()
    if should_plot:
        plot_gantt(edf_hist_wcet, tasks, "EDF", duration, prefix=prefix, mode="wcet")

    dm_sim_wcet = Scheduler(tasks, algorithm="DM", execution_mode="wcet", seed=42)
    _, dm_hist_wcet = dm_sim_wcet.run(duration, record_history=should_plot)
    dm_stats_wcet = dm_sim_wcet.analyze_results()
    if should_plot:
        plot_gantt(dm_hist_wcet, tasks, "DM", duration, prefix=prefix, mode="wcet")

    # Random simulation: for BCET~WCET runtime behavior
    rm_sim_rand = Scheduler(tasks, algorithm="RM", execution_mode="random", seed=42)
    rm_sim_rand.run(duration, record_history=False)
    rm_stats_rand = rm_sim_rand.analyze_results()

    edf_sim_rand = Scheduler(tasks, algorithm="EDF", execution_mode="random", seed=42)
    edf_sim_rand.run(duration, record_history=False)
    edf_stats_rand = edf_sim_rand.analyze_results()

    dm_sim_rand = Scheduler(tasks, algorithm="DM", execution_mode="random", seed=42)
    dm_sim_rand.run(duration, record_history=False)
    dm_stats_rand = dm_sim_rand.analyze_results()

    # --------------------------------------------------------------
    # Comparison report
    # --------------------------------------------------------------
    print_and_log("\n" + "=" * 40)
    print_and_log("          COMPARISON REPORT")
    print_and_log("=" * 40)

    comparison_data = []
    for t in tasks:
        tid = t.id

        comparison_data.append({
            "Task": f"T{tid}",

            "Analytic_WCRT(RM)": rm_analysis[tid]["WCRT_Analytic"],
            "Analytic_WCRT(DM)": dm_analysis[tid]["WCRT_Analytic"],
            "Analytic_WCRT(EDF)": edf_analysis[tid]["WCRT_Analytic"],

            "Sim_WCRT_WCET(RM)": rm_stats_wcet[tid]["Sim_WCRT"],
            "Sim_WCRT_WCET(DM)": dm_stats_wcet[tid]["Sim_WCRT"],
            "Sim_WCRT_WCET(EDF)": edf_stats_wcet[tid]["Sim_WCRT"],

            "Sim_WCRT_Random(RM)": rm_stats_rand[tid]["Sim_WCRT"],
            "Sim_WCRT_Random(DM)": dm_stats_rand[tid]["Sim_WCRT"],
            "Sim_WCRT_Random(EDF)": edf_stats_rand[tid]["Sim_WCRT"],

            "RM_Missed_WCET": rm_stats_wcet[tid]["Missed"],
            "DM_Missed_WCET": dm_stats_wcet[tid]["Missed"],
            "EDF_Missed_WCET": edf_stats_wcet[tid]["Missed"],

            "RM_Missed_Random": rm_stats_rand[tid]["Missed"],
            "DM_Missed_Random": dm_stats_rand[tid]["Missed"],
            "EDF_Missed_Random": edf_stats_rand[tid]["Missed"],
        })

    df_comp = pd.DataFrame(comparison_data)
    comp_text = df_comp.to_string(index=False)
    print(comp_text)
    log_only(comp_text)

    # --------------------------------------------------------------
    # Validation
    # Only validate upper-bound property for schedulable tasks
    # --------------------------------------------------------------
    print_and_log("\n--- Upper-bound validation against WCET simulation ---")

    valid = True
    checked = 0
    skipped = 0
    for t in tasks:
        tid = t.id

        checks = [
            ("RM", rm_analysis[tid]["Schedulable"], rm_analysis[tid]["WCRT_Analytic"], rm_stats_wcet[tid]["Sim_WCRT"]),
            ("DM", dm_analysis[tid]["Schedulable"], dm_analysis[tid]["WCRT_Analytic"], dm_stats_wcet[tid]["Sim_WCRT"]),
            ("EDF", edf_analysis[tid]["Schedulable"], edf_analysis[tid]["WCRT_Analytic"], edf_stats_wcet[tid]["Sim_WCRT"]),
        ]

        for alg, schedulable, analytic, sim in checks:
            if not schedulable or analytic == float("inf"):
                skipped += 1
                continue

            checked += 1
            if sim > analytic:
                msg = (
                    f"DISCREPANCY ({alg}): T{tid} "
                    f"simulated WCRT {sim} > analytic WCRT {analytic}"
                )
                print_and_log(msg)
                valid = False

    if valid:
        print_and_log(
            f"Upper-bound validation passed for analytically schedulable tasks "
            f"({checked} checks, {skipped} skipped unschedulable/infinite cases)."
        )
    else:
        print_and_log(
            f"Upper-bound validation FAILED "
            f"({checked} checks, {skipped} skipped unschedulable/infinite cases)."
        )


# ----------------------------------------------------------------------
# Batch runner
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    TASKSETS_NS_DIR = BASE_DIR / "tasksets" / "not_schedulable"
    TASKSETS_S_DIR = BASE_DIR / "tasksets" / "schedulable"

    schedulable_files = [
        "Full_Utilization_Unique_Periods_taskset.csv",
        "High_Utilization_NonUnique_Periods_taskset.csv",
    ]

    rm_unsched_but_edf_possible_files = [
        "Unschedulable_Full_Utilization_Unique_Periods_taskset.csv",
        "Unschedulable_High_Utilization_NonUnique_Periods_taskset.csv",
        "Unschedulable_High_Utilization_Unique_Periods_taskset.csv",
    ]

    overloaded_files = [
        "Unschedulable_Full_Utilization_NonUnique_Periods_taskset.csv",
    ]

    print_and_log("\n" + "=" * 60)
    print_and_log("  TASK SETS SCHEDULABLE BY RM/DM AND EDF")
    print_and_log("=" * 60)
    for name in schedulable_files:
        f = TASKSETS_S_DIR / name
        if f.exists():
            main(f)
        else:
            print_and_log(f"WARNING: File not found: {f}")

    print_and_log("\n" + "=" * 60)
    print_and_log("  TASK SETS NOT SCHEDULABLE BY RM/DM (EDF MAY SUCCEED)")
    print_and_log("=" * 60)
    for name in rm_unsched_but_edf_possible_files:
        f = TASKSETS_NS_DIR / name
        if f.exists():
            main(f)
        else:
            print_and_log(f"WARNING: File not found: {f}")

    print_and_log("\n" + "=" * 60)
    print_and_log("  OVERLOADED TASK SETS (NOT SCHEDULABLE ON ONE CPU)")
    print_and_log("=" * 60)
    for name in overloaded_files:
        f = TASKSETS_NS_DIR / name
        if f.exists():
            main(f)
        else:
            print_and_log(f"WARNING: File not found: {f}")
