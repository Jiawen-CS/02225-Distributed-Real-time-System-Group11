import csv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import MatplotlibDeprecationWarning

from model import Task
from analysis import perform_rm_analysis, check_ll_bound, calculate_utilization, perform_dm_analysis
from simulation import Scheduler

import warnings
warnings.filterwarnings(
    "ignore",
    category=MatplotlibDeprecationWarning
)

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

def load_tasks_from_csv(filename):
    tasks = []
    try:
        # Use utf-8-sig to handle potential BOM characters in CSV files created by Excel/TextEdit
        with open(filename, 'r', encoding='utf-8-sig') as f:
            # Skip initial whitespace if any
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                # Skip if TaskID is empty (handling trailing lines)
                if not row.get('Task'): continue
                
                tasks.append(Task(
                    id=int(row['Task']),
                    bcet=int(row.get('BCET')),
                    wcet=int(row['WCET']),
                    period=int(row['Period']),
                    deadline=int(row['Deadline']),
                    priority=int(row.get('Priority'))
                ))
    except FileNotFoundError:
        print("CSV not found, please check your file path.")
        tasks = []
    except KeyError as e:
        print(f"Error parsing CSV: Missing column {e}")
        tasks = []
    except ValueError as e:
        print(f"Error parsing CSV value: {e}")
        tasks = []
    return tasks

def plot_gantt(history, tasks, algorithm, duration):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Color map
    colors = plt.cm.get_cmap('tab10', len(tasks))
    task_colors = {t.id: colors(i) for i, t in enumerate(tasks)}
    
    # PERFORMANCE OPTIMIZATION: Merge consecutive blocks
    # Instead of drawing 240,000 rectangles of width 1, we draw consolidated blocks.
    # This reduces rendering time from minutes to seconds.
    merged_blocks = []
    if history:
        current_start_time = history[0][0]
        current_task_id = history[0][1]
        
        for t, task_id in history:
            if task_id != current_task_id:
                # The task changed, save the previous block
                if current_task_id is not None:
                    merged_blocks.append((current_start_time, t - current_start_time, current_task_id))
                
                # Start new block
                current_task_id = task_id
                current_start_time = t
        
        # Add the final block
        if current_task_id is not None:
            # The simulation runs up to 'duration', so the last block ends at 'duration' (or history length)
            # The loop variable 't' holds the last time index.
            last_t = history[-1][0] + 1
            merged_blocks.append((current_start_time, last_t - current_start_time, current_task_id))

    # Plot consolidated blocks
    for start, length, task_id in merged_blocks:
        ax.broken_barh([(start, length)], (task_id * 10, 9), facecolors=task_colors[task_id])
            
    # Labels
    ax.set_ylim(0, max([t.id for t in tasks]) * 10 + 10)
    # Set x-limit to the full duration
    ax.set_xlim(0, duration)
    ax.set_xlabel('Time')
    ax.set_ylabel('Task ID')
    ax.set_yticks([x * 10 + 4.5 for x in [t.id for t in tasks]])
    ax.set_yticklabels([f'T{t.id}' for t in tasks])
    ax.set_title(f'Gantt Chart - {algorithm} Scheduling (Duration: {duration})')
    ax.grid(True, axis='x')
    
    plt.savefig(f'{BASE_DIR}/resultplots/gantt_{algorithm}.png')
    print(f"Chart saved to gantt_{algorithm}.png")

def main(task_file):
    # 1. Load Data
    print("Loading Task Set...")
    tasks = load_tasks_from_csv(task_file)
    
    if not tasks:
        print("No tasks loaded. Exiting.")
        return

    # 2. Analytical Part
    print("\n" + "="*30)
    print("      ANALYTICAL RESULTS      ")
    print("="*30)
    
    u = calculate_utilization(tasks)
    is_schedulable, _, ll_bound = check_ll_bound(tasks)
    
    print(f"Total Utilization U: {u:.4f}")
    print(f"Liu & Layland Bound: {ll_bound:.4f}")
    print(f"Schedulable by LL Test? {'Yes' if is_schedulable else 'Inconclusive (Requires Exact Analysis)'}")
    
    if u > 1:
        print("WARNING: U > 1. System is overloaded. Deadlines will be missed.")
    
    # RM Exact Analysis (WCRT)
    rm_analysis = perform_rm_analysis(tasks)
    df_analytic = pd.DataFrame(rm_analysis).T
    print("\n--- RM Exact WCRT Analysis ---")
    print(df_analytic[['Period', 'WCET', 'WCRT_Analytic', 'Schedulable']])
    
    # DM Exact Analysis (WCRT)
    dm_analysis = perform_dm_analysis(tasks)
    df_analytic_dm = pd.DataFrame(dm_analysis).T
    print("\n--- DM Exact WCRT Analysis ---")
    print(df_analytic_dm[['Period', 'Deadline', 'WCET', 'WCRT_Analytic', 'Schedulable']])

    # 3. Simulation Part
    print("\n" + "="*30)
    print("      SIMULATION RESULTS      ")
    print("="*30)
    
    # --- RM Simulation ---
    rm_sim = Scheduler(tasks, algorithm="RM")    
    duration = rm_sim.hyperperiod
    if duration == 0: duration = 100 # Fallback for empty sets
    
    print(f"Hyperperiod (LCM): {duration}")

    rm_jobs, rm_history = rm_sim.run(duration)
    rm_stats = rm_sim.analyze_results()
    plot_gantt(rm_history, tasks, "RM", duration)

    # --- EDF Simulation ---
    edf_sim = Scheduler(tasks, algorithm="EDF")
    edf_jobs, edf_history = edf_sim.run(duration)
    edf_stats = edf_sim.analyze_results()
    plot_gantt(edf_history, tasks, "EDF", duration)
    
    # --- DM Simulation ---
    dm_sim = Scheduler(tasks, algorithm="DM")
    dm_jobs, dm_history = dm_sim.run(duration)
    dm_stats = dm_sim.analyze_results()
    plot_gantt(dm_history, tasks, "DM", duration)

    # 4. Comparison & Validation
    print("\n" + "="*30)
    print("      COMPARISON REPORT       ")
    print("="*30)
    
    comparison_data = []
    for t in tasks:
        t_id = t.id
        # Safe access to stats with default values in case of mismatch
        rm_stat = rm_stats.get(t_id, {"Sim_WCRT": -1, "Missed": -1})
        edf_stat = edf_stats.get(t_id, {"Sim_WCRT": -1, "Missed": -1})
        dm_stat = dm_stats.get(t_id, {"Sim_WCRT": -1, "Missed": -1})
        
        row = {
            "Task": f"T{t_id}",
            "Analytic_WCRT(RM)": rm_analysis[t_id]['WCRT_Analytic'],
            "Analytic_WCRT(DM)": dm_analysis[t_id]['WCRT_Analytic'],
            "Sim_WCRT(RM)": rm_stat['Sim_WCRT'],
            "Sim_WCRT(EDF)": edf_stat['Sim_WCRT'],
            "Sim_WCRT(DM)": dm_stat['Sim_WCRT'],
            "RM_Missed": rm_stat['Missed'],
            "EDF_Missed": edf_stat['Missed'],
            "DM_Missed": dm_stat['Missed']
        }
        comparison_data.append(row)
    
    df_comp = pd.DataFrame(comparison_data)
    
    with pd.option_context(
    'display.max_columns', None,
    'display.width', None,
    'display.max_colwidth', None
    ):
        print(df_comp)
    
    # Validation Check
    # Validation Check
    print("\n--- Validation Note ---")
    valid = True
    for index, row in df_comp.iterrows():
        # Analytic WCRT should be >= Observed Sim WCRT for RM
        if row['Analytic_WCRT(RM)'] < row['Sim_WCRT(RM)']:
            print(f"DISCREPANCY (RM): Task {row['Task']} simulated response {row['Sim_WCRT(RM)']} > predicted {row['Analytic_WCRT(RM)']}!")
            valid = False
        
        # Analytic WCRT should be >= Observed Sim WCRT for DM
        if row['Analytic_WCRT(DM)'] < row['Sim_WCRT(DM)']:
            print(f"DISCREPANCY (DM): Task {row['Task']} simulated response {row['Sim_WCRT(DM)']} > predicted {row['Analytic_WCRT(DM)']}!")
            valid = False
            
    if valid:
        print("Validation Successful: Analytic WCRT bounds held true for RM and DM simulations.")
    else:
        print("Validation Failed: Simulation exceeded analytic bounds.")

if __name__ == "__main__":
    TASKSETS_NS_DIR = BASE_DIR / "tasksets/not_schedulable"
    TASKSETS_S_DIR = BASE_DIR / "tasksets/schedulable"
    
    taskFile = TASKSETS_S_DIR/"Full_Utilization_NonUnique_Periods_taskset.csv"
    print(f"filedir: {taskFile}")
    main(taskFile)