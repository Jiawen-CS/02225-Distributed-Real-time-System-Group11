import csv
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from src.model import Task
from src.analysis import (
    perform_rm_analysis,
    perform_dm_analysis,
    perform_edf_analysis,
    calculate_utilization,
    check_ll_bound,
)
from src.simulation import Scheduler
from src.utils import print_and_log, log_only, set_log_file


BASE_DIR = Path(__file__).resolve().parent.parent

LOG_FILE = BASE_DIR / "logs" / "simulation.txt"

PLOTS_DIR = BASE_DIR / "plots_random_vs_analytic"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

GANTT_DIR = BASE_DIR / "gantt_random_vs_analytic"
GANTT_DIR.mkdir(parents=True, exist_ok=True)

CSV_DIR = BASE_DIR / "comparison_csv"
CSV_DIR.mkdir(parents=True, exist_ok=True)

SIMULATION_HYPERPERIODS = 45

PLOT_SIMULATION_GANTT = False
PLOT_ANALYTIC_GANTT = False

MAX_GANTT_DURATION = 200000

set_log_file(LOG_FILE)

# ----------------------------------------------------------------------
# Plot Gantt
# ----------------------------------------------------------------------
def plot_gantt(history, tasks, algorithm, duration, prefix="", mode="simulation"):
    fig, ax = plt.subplots(figsize=(14, 6))

    colors = plt.cm.get_cmap("tab10", len(tasks))
    task_colors = {t.id: colors(i) for i, t in enumerate(tasks)}

    for start, end, tid in history:

        if tid is None:
            continue

        ax.broken_barh(
            [(start, end - start)],
            (tid * 10, 9),
            facecolors=task_colors[tid]
        )

    ax.set_ylim(0, max(t.id for t in tasks) * 10 + 10)
    ax.set_xlim(0, duration)

    ax.set_xlabel("Time")
    ax.set_ylabel("Task ID")

    ax.set_yticks([t.id * 10 + 4.5 for t in tasks])
    ax.set_yticklabels([f"T{t.id}" for t in tasks])

    ax.set_title(
        f"{algorithm} Gantt Chart ({mode}) - {prefix}"
    )

    ax.grid(True, axis="x")

    out_path = (
        GANTT_DIR /
        f"{prefix}_{algorithm}_{mode}_gantt.png"
    )

    plt.savefig(out_path)
    plt.close()

    print_and_log(f"Saved Gantt chart: {out_path}")


def generate_analytic_schedule(tasks, algorithm, hyperperiods=1):

    scheduler = Scheduler(
        tasks,
        algorithm=algorithm,
        execution_mode="wcet",
        seed=42,
    )

    duration = scheduler.hyperperiod * hyperperiods

    _, history = scheduler.run(
        duration=duration,
        record_history=True
    )

    return history, duration

# ----------------------------------------------------------------------
# CSV loader
# ----------------------------------------------------------------------
def load_tasks_from_csv(filename):
    tasks = []

    with open(filename, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, skipinitialspace=True)

        for row in reader:
            if not row.get("Task"):
                continue

            tid = int(row["Task"].split("_")[1])

            tasks.append(Task(
                name=row["Task"],
                id=tid,
                bcet=int(row.get("BCET", row["WCET"])),
                wcet=int(row["WCET"]),
                period=int(row["Period"]),
                deadline=int(row["Deadline"]),
                priority=int(row.get("Priority", 0)),
            ))

    return tasks


# ----------------------------------------------------------------------
# Collect all response times from simulation
# ----------------------------------------------------------------------
def collect_response_times(scheduler):
    response_times = {t.id: [] for t in scheduler.tasks}

    for job in scheduler.completed_jobs:
        if (
            not job.force_finished
            and job.response_time is not None
        ):
            response_times[job.task_id].append(job.response_time)

    return response_times


# ----------------------------------------------------------------------
# Plot distribution
# ----------------------------------------------------------------------
def plot_distribution(
    task_id,
    algorithm,
    simulation_mode,
    analytic_wcrt,
    simulated_rts,
    prefix
):
    plt.figure(figsize=(8, 5))

    if simulated_rts:
        plt.hist(simulated_rts, bins=20)

    plt.axvline(
        analytic_wcrt,
        linestyle="--",
        linewidth=2,
        label=f"Analytical WCRT = {analytic_wcrt}"
    )

    plt.xlabel("Observed Response Time")
    plt.ylabel("Frequency")

    plt.title(
        f"{algorithm} - {simulation_mode.replace('_', ' ').upper()} - Task {task_id}\n"
        f"Analytical vs Simulation Distribution"
    )

    plt.legend()

    out_path = (
        PLOTS_DIR /
        f"{prefix}_{algorithm}_{simulation_mode}_Task_{task_id}_distribution.png"
    )

    plt.savefig(out_path)
    plt.close()

    print_and_log(f"Saved plot: {out_path}")

# ----------------------------------------------------------------------
# Run random simulation
# ----------------------------------------------------------------------
def run_simulation(
    tasks,
    algorithm,
    execution_mode,
    hyperperiods=45,
    record_history=False,
):
    scheduler = Scheduler(
        tasks,
        algorithm=algorithm,
        execution_mode=execution_mode,
        seed=42,
    )

    duration = scheduler.hyperperiod * hyperperiods

    _, history = scheduler.run(
        duration=duration,
        record_history=record_history
    )

    stats = scheduler.analyze_results()

    response_times = collect_response_times(scheduler)

    return scheduler, stats, response_times, history, duration

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main(task_file):
    prefix = Path(task_file).stem

    print_and_log("\n" + "=" * 60)
    print_and_log(f"TASK SET: {prefix}")
    print_and_log("=" * 60)

    tasks = load_tasks_from_csv(task_file)

    if not tasks:
        print_and_log("No tasks loaded.")
        return

    # ==============================================================
    # ANALYTICAL
    # ==============================================================
    print_and_log("\n" + "=" * 40)
    print_and_log("ANALYTICAL RESULTS")
    print_and_log("=" * 40)

    u = calculate_utilization(tasks)
    ll_ok, _, ll_bound = check_ll_bound(tasks)

    print_and_log(f"Utilization U        : {u:.4f}")
    print_and_log(f"LL Bound             : {ll_bound:.4f}")
    print_and_log(f"LL Test Passed       : {ll_ok}")

    rm_analysis = perform_rm_analysis(tasks)
    dm_analysis = perform_dm_analysis(tasks)
    edf_analysis = perform_edf_analysis(tasks)

    df_rm = pd.DataFrame(rm_analysis).T
    df_dm = pd.DataFrame(dm_analysis).T
    df_edf = pd.DataFrame(edf_analysis).T

    print_and_log("\n--- RM ANALYSIS ---")
    print(df_rm[["WCRT_Analytic", "Schedulable"]])
    log_only(df_rm.to_string())

    print_and_log("\n--- DM ANALYSIS ---")
    print(df_dm[["WCRT_Analytic", "Schedulable"]])
    log_only(df_dm.to_string())

    print_and_log("\n--- EDF ANALYSIS ---")
    print(df_edf[["WCRT_Analytic", "Schedulable"]])
    log_only(df_edf.to_string())

    if PLOT_ANALYTIC_GANTT:

        print_and_log("\nGenerating analytical Gantt charts...")

        rm_hist_a, rm_dur_a = generate_analytic_schedule(tasks, "RM")
        dm_hist_a, dm_dur_a = generate_analytic_schedule(tasks, "DM")
        edf_hist_a, edf_dur_a = generate_analytic_schedule(tasks, "EDF")

        if rm_dur_a <= MAX_GANTT_DURATION:
            plot_gantt(
                rm_hist_a,
                tasks,
                "RM",
                rm_dur_a,
                prefix,
                mode="analytic"
            )

        if dm_dur_a <= MAX_GANTT_DURATION:
            plot_gantt(
                dm_hist_a,
                tasks,
                "DM",
                dm_dur_a,
                prefix,
                mode="analytic"
            )

        if edf_dur_a <= MAX_GANTT_DURATION:
            plot_gantt(
                edf_hist_a,
                tasks,
                "EDF",
                edf_dur_a,
                prefix,
                mode="analytic"
            )

    # ==============================================================
    # RANDOM SIMULATION
    # ==============================================================
    print_and_log("\n" + "=" * 40)
    print_and_log("SIMULATION RESULTS")
    print_and_log("=" * 40)

    simulation_modes = [
        "bcet",
        "wcet",
        "random_uniform",
        "random_bcet",
        "random_wcet",
    ]

    simulation_results = {}

    for sim_mode in simulation_modes:

        print_and_log("\n" + "-" * 40)
        print_and_log(f"{sim_mode.upper()} SIMULATION")
        print_and_log("-" * 40)

        simulation_results[sim_mode] = {}

        for alg in ["RM", "DM", "EDF"]:

            pretty_mode = sim_mode.replace("_", " ").upper()

            print_and_log(
                f"Running {alg} ({pretty_mode}) simulation "
                f"for {SIMULATION_HYPERPERIODS} hyperperiods"
            )

            sched, stats, rts, hist, duration = run_simulation(
                tasks,
                algorithm=alg,
                execution_mode=sim_mode,
                hyperperiods=SIMULATION_HYPERPERIODS,
                record_history=PLOT_SIMULATION_GANTT,
            )

            simulation_results[sim_mode][alg] = {
                "scheduler": sched,
                "stats": stats,
                "rts": rts,
                "history": hist,
                "duration": duration,
            }

            # ------------------------------------------------------
            # Gantt charts
            # ------------------------------------------------------
            if (
                    PLOT_SIMULATION_GANTT
                    and duration <= MAX_GANTT_DURATION
            ):
                plot_gantt(
                    hist,
                    tasks,
                    f"{alg}_{sim_mode}",
                    duration,
                    prefix,
                    mode="simulation"
                )

    # ==============================================================
    # COMPARISON REPORT
    # ==============================================================

    print_and_log("\n" + "=" * 40)
    print_and_log("COMPARISON REPORT")
    print_and_log("=" * 40)

    analysis_lookup = {
        "RM": rm_analysis,
        "DM": dm_analysis,
        "EDF": edf_analysis,
    }

    for sim_mode in simulation_modes:

        pretty_mode = sim_mode.replace("_", " ").upper()

        print_and_log("\n" + "-" * 60)
        print_and_log(f"ANALYTICAL vs {pretty_mode}")
        print_and_log("-" * 60)

        rows = []

        all_gaps = {
            "RM": [],
            "DM": [],
            "EDF": [],
        }

        for t in tasks:

            tid = t.id

            row = {
                "Task": f"T{tid}",
            }

            for alg in ["RM", "DM", "EDF"]:
                analytic = \
                    analysis_lookup[alg][tid]["WCRT_Analytic"]

                sim_stats = \
                    simulation_results[sim_mode][alg]["stats"]

                observed = sim_stats[tid]["Sim_WCRT"]

                missed = sim_stats[tid]["Missed"]

                gap = analytic - observed

                row[f"{alg}_Analytic"] = analytic
                row[f"{alg}_Observed"] = observed
                row[f"{alg}_Gap"] = gap
                row[f"{alg}_Missed"] = missed

                all_gaps[alg].append(gap)

            rows.append(row)

        # ----------------------------------------------------------
        # Table
        # ----------------------------------------------------------
        df = pd.DataFrame(rows)

        print(df.to_string(index=False))
        log_only(df.to_string(index=False))

        # ----------------------------------------------------------
        # Save CSV
        # ----------------------------------------------------------
        csv_path = (
                CSV_DIR /
                f"{prefix}_{sim_mode}_comparison.csv"
        )

        df.to_csv(csv_path, index=False)

        print_and_log(f"\nSaved CSV: {csv_path}")

        # ----------------------------------------------------------
        # Statistics
        # ----------------------------------------------------------
        print_and_log("\nGap Statistics:")

        for alg in ["RM", "DM", "EDF"]:
            gaps = np.array(all_gaps[alg])

            mean_gap = np.mean(gaps)
            variance_gap = np.var(gaps)

            print_and_log(f"\n{alg}:")

            print_and_log(
                f"  Gaps     : {gaps.tolist()}"
            )

            print_and_log(
                f"  Mean Gap : {mean_gap:.4f}"
            )

            print_and_log(
                f"  Variance : {variance_gap:.4f}"
            )

    # ==============================================================
    # DISTRIBUTION PLOTS
    # ==============================================================

    print_and_log("\nGenerating distribution plots...")

    for sim_mode in simulation_modes:

        for alg in ["RM", "DM", "EDF"]:

            sim_rts = simulation_results[sim_mode][alg]["rts"]

            for t in tasks:

                tid = t.id

                if alg == "RM":
                    analytic_wcrt = rm_analysis[tid]["WCRT_Analytic"]

                elif alg == "DM":
                    analytic_wcrt = dm_analysis[tid]["WCRT_Analytic"]

                else:
                    analytic_wcrt = edf_analysis[tid]["WCRT_Analytic"]

                plot_distribution(
                    tid,
                    alg,
                    sim_mode,
                    analytic_wcrt,
                    sim_rts[tid],
                    prefix
                )

    print_and_log("\nFinished.")


# ----------------------------------------------------------------------
# Batch runner
# ----------------------------------------------------------------------
if __name__ == "__main__":

    TASKSETS_DIR = BASE_DIR / "tasksets" / "simulation_tasksets"

    taskset_files = [
        f for f in os.listdir(TASKSETS_DIR)
        if os.path.isfile(os.path.join(TASKSETS_DIR, f))
    ]

    for filename in taskset_files:
        main(TASKSETS_DIR / filename)