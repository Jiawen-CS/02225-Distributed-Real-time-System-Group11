# analysis.py
import math
from model import Task


def calculate_utilization(tasks):
    """Sum of Ci/Ti for all tasks."""
    return sum(t.utilization() for t in tasks)


def check_ll_bound(tasks):
    """Liu & Layland schedulability bound: U <= n * (2^(1/n) - 1)."""
    n = len(tasks)
    u = calculate_utilization(tasks)
    bound = n * (2 ** (1 / n) - 1)
    return u <= bound, u, bound


def calculate_exact_wcrt_rm(task: Task, higher_priority_tasks: list[Task]):
    """
    Iterative fixed-point algorithm for Worst-Case Response Time under
    static-priority scheduling (used by both RM and DM):
        R = Ci + Sum( ceil(R / Tj) * Cj )  for all higher-priority tasks j
    Returns R when converged, or R > Di if unschedulable.
    """
    R_curr = task.wcet
    while True:
        interference = sum(
            math.ceil(R_curr / hp.period) * hp.wcet
            for hp in higher_priority_tasks
        )
        R_new = task.wcet + interference

        if R_new > task.deadline:
            return R_new        # Unschedulable: exceeded deadline
        if R_new == R_curr:
            return R_new        # Converged to fixed point
        R_curr = R_new


def perform_rm_analysis(tasks):
    """
    Full Response Time Analysis for Rate Monotonic scheduling.
    Priority order: shorter period -> higher priority (tie-break by ID).
    """
    sorted_tasks = sorted(tasks, key=lambda x: (x.period, x.id))
    results = {}
    for i, task in enumerate(sorted_tasks):
        hp_tasks = sorted_tasks[:i]
        wcrt = calculate_exact_wcrt_rm(task, hp_tasks)
        results[task.id] = {
            "Task":           f"Task {task.id}",
            "Period":         task.period,
            "WCET":           task.wcet,
            "WCRT_Analytic":  wcrt,
            "Schedulable":    wcrt <= task.deadline,
        }
    return results


def perform_dm_analysis(tasks):
    """
    Full Response Time Analysis for Deadline Monotonic scheduling.
    Priority order: shorter relative deadline -> higher priority (tie-break by ID).
    """
    sorted_tasks = sorted(tasks, key=lambda x: (x.deadline, x.id))
    results = {}
    for i, task in enumerate(sorted_tasks):
        hp_tasks = sorted_tasks[:i]
        wcrt = calculate_exact_wcrt_rm(task, hp_tasks)   # Same interference formula
        results[task.id] = {
            "Task":           f"Task {task.id}",
            "Period":         task.period,
            "Deadline":       task.deadline,
            "WCET":           task.wcet,
            "WCRT_Analytic":  wcrt,
            "Schedulable":    wcrt <= task.deadline,
        }
    return results


def perform_edf_analysis(tasks):
    """
    Exact WCRT analysis for EDF over one hyperperiod, as specified in the
    project appendix:
      1. Compute H = lcm of all periods.
      2. Generate every job released in [0, H).
      3. Simulate EDF (earliest absolute deadline first) with every job
         running for exactly its WCET (worst-case load).
      4. WCRT_i = max response time observed among all jobs of task i.

    This gives the exact theoretical upper bound for the synchronous,
    strictly-periodic task model.
    """
    periods = [t.period for t in tasks]
    H = math.lcm(*periods)

    # --- Step 1: Generate all jobs in [0, H) ---
    all_jobs = []
    for task in tasks:
        k = 0
        while k * task.period < H:
            release = k * task.period
            all_jobs.append({
                "task_id":   task.id,
                "release":   release,
                "deadline":  release + task.deadline,
                "remaining": task.wcet,
                "finish":    -1,
            })
            k += 1

    # --- Step 2: Simulate EDF ---
    # Run until H plus a margin (one extra WCET) to let the last jobs finish
    max_wcet = max(t.wcet for t in tasks)
    for t in range(H + max_wcet):
        # Collect jobs that have arrived and are not yet finished
        ready = [j for j in all_jobs if j["release"] <= t and j["finish"] == -1]
        if not ready:
            continue
        # EDF rule: pick job with earliest absolute deadline (tie-break: earlier release)
        job = min(ready, key=lambda j: (j["deadline"], j["release"]))
        job["remaining"] -= 1
        if job["remaining"] == 0:
            job["finish"] = t + 1   # Job completes at the end of time slot t

    # --- Step 3: Compute per-task WCRT ---
    results = {}
    for task in tasks:
        jobs = [j for j in all_jobs if j["task_id"] == task.id]
        if not jobs or any(j["finish"] == -1 for j in jobs):
            # Some jobs never finished -> unschedulable
            wcrt = float("inf")
            schedulable = False
        else:
            response_times = [j["finish"] - j["release"] for j in jobs]
            wcrt = max(response_times)
            schedulable = wcrt <= task.deadline

        results[task.id] = {
            "Task":          f"Task {task.id}",
            "Period":        task.period,
            "Deadline":      task.deadline,
            "WCET":          task.wcet,
            "WCRT_Analytic": wcrt,
            "Schedulable":   schedulable,
        }
    return results