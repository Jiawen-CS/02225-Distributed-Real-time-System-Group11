import math
import heapq
from model import Task


def calculate_utilization(tasks):
    """Sum of Ci/Ti for all tasks."""
    return sum(t.utilization() for t in tasks)


def check_ll_bound(tasks):
    """
    Liu & Layland schedulability bound for RM:
        U <= n * (2^(1/n) - 1)

    This bound is sufficient but not necessary.
    """
    n = len(tasks)
    u = calculate_utilization(tasks)
    bound = n * (2 ** (1 / n) - 1)
    return u <= bound, u, bound


def calculate_exact_wcrt_fp(task: Task, higher_priority_tasks: list[Task]):
    """
    Fixed-priority exact response-time analysis (used by RM and DM):

        R_i = C_i + sum( ceil(R_i / T_j) * C_j )

    Returns:
        - converged WCRT if schedulable
        - first value exceeding deadline if unschedulable
    """
    R_curr = task.wcet

    while True:
        interference = sum(
            math.ceil(R_curr / hp.period) * hp.wcet
            for hp in higher_priority_tasks
        )
        R_new = task.wcet + interference

        if R_new > task.deadline:
            return R_new  # enough to conclude unschedulable
        if R_new == R_curr:
            return R_new  # converged

        R_curr = R_new


def perform_rm_analysis(tasks):
    """
    Exact WCRT analysis for Rate Monotonic.
    Priority: shorter period -> higher priority.
    """
    sorted_tasks = sorted(tasks, key=lambda x: (x.period, x.id))
    results = {}

    for i, task in enumerate(sorted_tasks):
        hp_tasks = sorted_tasks[:i]
        wcrt = calculate_exact_wcrt_fp(task, hp_tasks)

        results[task.id] = {
            "Task": f"Task {task.id}",
            "Period": task.period,
            "Deadline": task.deadline,
            "WCET": task.wcet,
            "WCRT_Analytic": wcrt,
            "Schedulable": wcrt <= task.deadline,
        }

    return results


def perform_dm_analysis(tasks):
    """
    Exact WCRT analysis for Deadline Monotonic.
    Priority: shorter relative deadline -> higher priority.
    """
    sorted_tasks = sorted(tasks, key=lambda x: (x.deadline, x.id))
    results = {}

    for i, task in enumerate(sorted_tasks):
        hp_tasks = sorted_tasks[:i]
        wcrt = calculate_exact_wcrt_fp(task, hp_tasks)

        results[task.id] = {
            "Task": f"Task {task.id}",
            "Period": task.period,
            "Deadline": task.deadline,
            "WCET": task.wcet,
            "WCRT_Analytic": wcrt,
            "Schedulable": wcrt <= task.deadline,
        }

    return results


def perform_edf_analysis(tasks):
    """
    Exact EDF WCRT analysis aligned with the teacher's appendix:

    Assumptions:
      - strictly periodic tasks
      - synchronous release (all first jobs released at t=0)
      - D_i <= T_i
      - every job executes exactly WCET
      - single processor

    Method:
      1. Compute H = lcm(T1, ..., Tn)
      2. Generate all jobs released in [0, H)
      3. Construct EDF schedule
      4. Record finish times
      5. WCRT_i = max(response times of all jobs of task i)

    Stopping rule:
      - if U < 1: simulate until H
      - if U == 1: simulate until CPU becomes idle after H
      - if U > 1: overloaded, whole task set unschedulable on one CPU
    """
    if not tasks:
        return {}

    EPS = 1e-9
    U = calculate_utilization(tasks)
    periods = [t.period for t in tasks]
    H = math.lcm(*periods)

    # Overloaded system: EDF cannot schedule all jobs on one CPU
    if U > 1 + EPS:
        return {
            task.id: {
                "Task": f"Task {task.id}",
                "Period": task.period,
                "Deadline": task.deadline,
                "WCET": task.wcet,
                "Hyperperiod": H,
                "WCRT_Analytic": float("inf"),
                "Schedulable": False,
            }
            for task in tasks
        }

    # Generate all jobs released in [0, H) and bucket them by release time
    all_jobs = []
    release_buckets = {}
    for task in tasks:
        k = 0
        while k * task.period < H:
            release = k * task.period
            job = {
                "task_id": task.id,
                "release": release,
                "deadline": release + task.deadline,
                "remaining": task.wcet,
                "finish": -1,
            }
            all_jobs.append(job)
            release_buckets.setdefault(release, []).append(job)
            k += 1

    # Simulate EDF with a priority heap instead of scanning every job each tick
    t = 0
    ready = []
    while True:
        for job in release_buckets.get(t, []):
            heapq.heappush(
                ready,
                ((job["deadline"], job["release"], job["task_id"]), job),
            )

        if ready:
            # EDF + deterministic tie-breaking
            _, job = heapq.heappop(ready)
            job["remaining"] -= 1
            if job["remaining"] == 0:
                job["finish"] = t + 1
            else:
                heapq.heappush(
                    ready,
                    ((job["deadline"], job["release"], job["task_id"]), job),
                )

        # Stop rules
        if U < 1 - EPS:
            if t + 1 >= H:
                break
        else:
            # U == 1 approximately: continue until no unfinished jobs released in [0, H)
            unfinished = any(
                j["release"] < H and j["finish"] == -1
                for j in all_jobs
            )
            if t + 1 >= H and not unfinished:
                break

        t += 1

    # Compute per-task WCRT
    results = {}
    for task in tasks:
        jobs = [j for j in all_jobs if j["task_id"] == task.id]

        if not jobs or any(j["finish"] == -1 for j in jobs):
            wcrt = float("inf")
            schedulable = False
        else:
            response_times = [j["finish"] - j["release"] for j in jobs]
            wcrt = max(response_times)
            schedulable = wcrt <= task.deadline

        results[task.id] = {
            "Task": f"Task {task.id}",
            "Period": task.period,
            "Deadline": task.deadline,
            "WCET": task.wcet,
            "Hyperperiod": H,
            "WCRT_Analytic": wcrt,
            "Schedulable": schedulable,
        }

    return results
