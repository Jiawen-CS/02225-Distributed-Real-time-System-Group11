# analysis.py
import math
from model import Task

def calculate_utilization(tasks):
    return sum(t.utilization() for t in tasks)

def check_ll_bound(tasks):
    """Liu and Layland Bound: U <= n(2^(1/n) - 1)"""
    n = len(tasks)
    u = calculate_utilization(tasks)
    bound = n * (2**(1/n) - 1)
    return u <= bound, u, bound

# def check_hyperbolic_bound(tasks):
#     """Hyperbolic Bound: Product(Ui + 1) <= 2"""
#     prod = 1.0
#     for t in tasks:
#         prod *= (t.utilization() + 1)
#     return prod <= 2, prod

def calculate_exact_wcrt_rm(task: Task, higher_priority_tasks: list[Task]):
    """
    Calculates the Worst-Case Response Time (Ri) for a task under RM
    using the iterative fixed-point algorithm:
    Ri = Ci + Sum( ceil(Ri / Tj) * Cj )
    """
    R_curr = task.wcet
    while True:
        interference = 0
        for hp_task in higher_priority_tasks:
            interference += math.ceil(R_curr / hp_task.period) * hp_task.wcet
        
        R_new = task.wcet + interference
        
        if R_new > task.deadline:
            return R_new  # Unschedulable
        if R_new == R_curr:
            return R_new  # Converged
        
        R_curr = R_new

def perform_rm_analysis(tasks):
    """
    Performs full Response Time Analysis (RTA) for RM.
    """
    # Sort by Period (Rate Monotonic: Shorter Period = Higher Priority)
    # Tie-breaker: ID
    sorted_tasks = sorted(tasks, key=lambda x: (x.period, x.id))
    
    results = {}
    
    for i, task in enumerate(sorted_tasks):
        hp_tasks = sorted_tasks[:i]
        wcrt = calculate_exact_wcrt_rm(task, hp_tasks)
        schedulable = wcrt <= task.deadline
        results[task.id] = {
            "Task": f"Task {task.id}",
            "Period": task.period,
            "WCET": task.wcet,
            "WCRT_Analytic": wcrt,
            "Schedulable": schedulable
        }
    return results