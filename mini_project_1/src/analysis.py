"""
analysis.py - Analytical Schedulability Engine for Real-Time Systems

Based on Giorgio Buttazzo's "Hard Real-Time Computing Systems" textbook.

This module implements exact schedulability analysis for:
  - Deadline Monotonic (DM) scheduling using Response Time Analysis (RTA)
  - Earliest Deadline First (EDF) scheduling using Processor Demand Criterion (PDC)

References:
  - Buttazzo, Chapter 4: Periodic Task Scheduling (RM, DM)
  - Buttazzo, Chapter 5: EDF Scheduling and Processor Demand Analysis
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

# Handle imports for both direct execution and module execution
try:
    from model import Task
except ImportError:
    from .model import Task


# =============================================================================
# Analysis Result Data Structures
# =============================================================================

@dataclass
class TaskAnalysisResult:
    """Result of schedulability analysis for a single task."""
    task_id: int
    task_name: str
    period: int           # T_i
    deadline: int         # D_i
    wcet: int             # C_i
    wcrt: Optional[int]   # R_i (Worst-Case Response Time), None if analysis failed
    schedulable: bool     # True if R_i ≤ D_i
    priority: int         # Assigned priority (lower = higher priority)


@dataclass 
class DMAnalysisResult:
    """Complete result of Deadline Monotonic schedulability analysis."""
    schedulable: bool                           # Overall schedulability
    total_utilization: float                    # U = Σ(C_i/T_i)
    task_results: Dict[int, TaskAnalysisResult] # Per-task analysis results
    priority_order: List[int]                   # Task IDs in priority order


@dataclass
class EDFAnalysisResult:
    """Complete result of EDF schedulability analysis."""
    schedulable: bool           # Overall schedulability
    total_utilization: float    # U = Σ(C_i/T_i)
    total_density: float        # Δ = Σ(C_i/D_i)
    l_star: Optional[float]     # Testing interval upper bound L*
    critical_point: Optional[int]  # L value where dbf(L) > L, if any
    utilization_test_passed: bool  # U ≤ 1 necessary condition


# =============================================================================
# Analytical Engine Class
# =============================================================================

class AnalyticalEngine:
    """
    Schedulability analysis engine based on Buttazzo's textbook.
    
    Implements exact analysis methods for static and dynamic priority scheduling:
      - DM (Deadline Monotonic): Response Time Analysis (RTA)
      - EDF (Earliest Deadline First): Processor Demand Criterion (PDC)
    
    Usage:
        engine = AnalyticalEngine(tasks)
        dm_result = engine.analyze_dm()
        edf_result = engine.analyze_edf()
    """
    
    def __init__(self, tasks: List[Task]):
        """
        Initialize the analytical engine with a task set.
        
        Args:
            tasks: List of Task objects to analyze
        """
        if not tasks:
            raise ValueError("Task set cannot be empty")
        
        self.tasks = tasks
        self.n = len(tasks)
        
        # Pre-compute utilization and density
        self._total_utilization = sum(t.utilization for t in tasks)
        self._total_density = sum(t.density for t in tasks)
    
    @property
    def total_utilization(self) -> float:
        """Total utilization U = Σ(C_i/T_i)."""
        return self._total_utilization
    
    @property
    def total_density(self) -> float:
        """Total density Δ = Σ(C_i/D_i)."""
        return self._total_density
    
    # =========================================================================
    # Deadline Monotonic (DM) Analysis - Response Time Analysis (RTA)
    # =========================================================================
    
    def analyze_dm(self) -> DMAnalysisResult:
        """
        Perform Deadline Monotonic schedulability analysis using exact RTA.
        
        From Buttazzo, Chapter 4:
        - DM assigns priorities based on relative deadlines (shorter D = higher priority)
        - For constrained deadlines (D_i ≤ T_i), DM is optimal among fixed-priority algorithms
        
        The Response Time Analysis iteratively computes:
            R_i^{(0)} = C_i
            R_i^{(s)} = C_i + Σ_{h∈hp(i)} ⌈R_i^{(s-1)} / T_h⌉ · C_h
        
        Convergence:
            - If R_i^{(s)} == R_i^{(s-1)}, task is schedulable with WCRT = R_i
            - If R_i^{(s)} > D_i, task is unschedulable
        
        Returns:
            DMAnalysisResult with schedulability verdict and per-task WCRTs
        """
        # Sort tasks by relative deadline (DM priority assignment)
        # Tie-breaker: task ID for deterministic ordering
        sorted_tasks = sorted(self.tasks, key=lambda t: (t.deadline, t.id))
        
        # Assign priorities (0 = highest priority)
        priority_order = [t.id for t in sorted_tasks]
        
        task_results: Dict[int, TaskAnalysisResult] = {}
        all_schedulable = True
        
        for priority, task in enumerate(sorted_tasks):
            # Higher priority tasks (those before current task in sorted order)
            hp_tasks = sorted_tasks[:priority]
            
            # Compute WCRT using RTA
            wcrt, schedulable = self._compute_wcrt_rta(task, hp_tasks)
            
            result = TaskAnalysisResult(
                task_id=task.id,
                task_name=task.name,
                period=task.period,
                deadline=task.deadline,
                wcet=task.wcet,
                wcrt=wcrt,
                schedulable=schedulable,
                priority=priority
            )
            task_results[task.id] = result
            
            if not schedulable:
                all_schedulable = False
        
        return DMAnalysisResult(
            schedulable=all_schedulable,
            total_utilization=self.total_utilization,
            task_results=task_results,
            priority_order=priority_order
        )
    
    def _compute_wcrt_rta(self, task: Task, hp_tasks: List[Task]) -> Tuple[Optional[int], bool]:
        """
        Compute Worst-Case Response Time using iterative RTA.
        
        Algorithm from Buttazzo, Theorem 4.2:
            R_i^{(0)} = C_i
            R_i^{(s)} = C_i + Σ_{h∈hp(i)} ⌈R_i^{(s-1)} / T_h⌉ · C_h
        
        Args:
            task: The task to analyze
            hp_tasks: List of higher-priority tasks
            
        Returns:
            Tuple of (wcrt, schedulable):
                - wcrt: The computed WCRT (may exceed deadline)
                - schedulable: True if wcrt ≤ deadline
        """
        # Initial guess: R_i^{(0)} = C_i
        R_curr = task.wcet
        
        # Maximum iterations to prevent infinite loops (should never be needed)
        max_iterations = 1000
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Compute interference from higher-priority tasks
            # I_i = Σ_{h∈hp(i)} ⌈R_i / T_h⌉ · C_h
            interference = 0
            for hp_task in hp_tasks:
                # Number of jobs of hp_task released in [0, R_curr)
                num_jobs = math.ceil(R_curr / hp_task.period)
                interference += num_jobs * hp_task.wcet
            
            # Update response time
            R_new = task.wcet + interference
            
            # Stop condition 1: Exceeds deadline → UNSCHEDULABLE
            # (Early termination optimization)
            if R_new > task.deadline:
                return R_new, False
            
            # Stop condition 2: Converged → SCHEDULABLE
            if R_new == R_curr:
                return R_new, True
            
            R_curr = R_new
        
        # Should never reach here with valid task sets
        raise RuntimeError(f"RTA did not converge for task {task.name} after {max_iterations} iterations")
    
    # =========================================================================
    # Earliest Deadline First (EDF) Analysis - Processor Demand Criterion
    # =========================================================================
    
    def analyze_edf(self) -> EDFAnalysisResult:
        """
        Perform EDF schedulability analysis using Processor Demand Criterion.
        
        From Buttazzo, Chapter 5 (Theorem 5.3):
        For constrained deadlines (D_i ≤ T_i), EDF is schedulable iff:
            ∀L ∈ [0, L*]: dbf(L) ≤ L
        
        where the Demand Bound Function is:
            dbf(L) = Σ_{i=1}^{n} max(0, ⌊(L + T_i - D_i) / T_i⌋) · C_i
        
        and L* (busy period upper bound) is:
            L* = Σ_{i=1}^{n} (T_i - D_i) · U_i / (1 - U)    if U < 1
        
        The testing set consists of absolute deadlines d_{i,k} = D_i + k·T_i
        that fall within [0, L*].
        
        Returns:
            EDFAnalysisResult with schedulability verdict
        """
        U = self.total_utilization
        
        # Necessary condition: U ≤ 1
        if U > 1.0:
            return EDFAnalysisResult(
                schedulable=False,
                total_utilization=U,
                total_density=self.total_density,
                l_star=None,
                critical_point=None,
                utilization_test_passed=False
            )
        
        # For implicit deadlines (D_i = T_i), U ≤ 1 is also sufficient
        all_implicit = all(t.deadline == t.period for t in self.tasks)
        if all_implicit:
            return EDFAnalysisResult(
                schedulable=True,
                total_utilization=U,
                total_density=self.total_density,
                l_star=None,
                critical_point=None,
                utilization_test_passed=True
            )
        
        # Compute L* (testing interval upper bound)
        # L* = Σ(T_i - D_i) · U_i / (1 - U)
        if U >= 1.0 - 1e-9:  # U ≈ 1, L* → ∞
            # Use hyperperiod as fallback
            l_star = self._compute_hyperperiod()
        else:
            numerator = sum((t.period - t.deadline) * t.utilization for t in self.tasks)
            l_star = numerator / (1.0 - U)
        
        # Round up L* and ensure it's at least max(D_i)
        l_star = max(l_star, max(t.deadline for t in self.tasks))
        l_star_int = int(math.ceil(l_star))
        
        # Generate testing set: all absolute deadlines d_{i,k} ≤ L*
        # d_{i,k} = D_i + k·T_i for k = 0, 1, 2, ...
        testing_points = self._generate_edf_testing_points(l_star_int)
        
        # Check demand bound at each testing point
        critical_point = None
        for L in testing_points:
            dbf_L = self._compute_dbf(L)
            if dbf_L > L:
                critical_point = L
                break
        
        schedulable = (critical_point is None)
        
        return EDFAnalysisResult(
            schedulable=schedulable,
            total_utilization=U,
            total_density=self.total_density,
            l_star=l_star,
            critical_point=critical_point,
            utilization_test_passed=True
        )
    
    def _compute_dbf(self, L: int) -> int:
        """
        Compute Demand Bound Function dbf(L).
        
        From Buttazzo, Definition 5.1:
            dbf(L) = Σ_{i=1}^{n} max(0, ⌊(L + T_i - D_i) / T_i⌋) · C_i
        
        This represents the maximum cumulative execution time requested by
        all tasks with deadlines ≤ L.
        
        Args:
            L: Time interval length
            
        Returns:
            Total processor demand in [0, L]
        """
        total_demand = 0
        for task in self.tasks:
            # Number of jobs with deadline ≤ L
            # Jobs have deadlines at D_i, D_i + T_i, D_i + 2·T_i, ...
            # Job k has deadline D_i + k·T_i ≤ L
            # So k ≤ (L - D_i) / T_i
            # Number of jobs = floor((L - D_i) / T_i) + 1 if L ≥ D_i, else 0
            
            # Using Buttazzo's formula: ⌊(L + T_i - D_i) / T_i⌋
            num_jobs = max(0, math.floor((L + task.period - task.deadline) / task.period))
            total_demand += num_jobs * task.wcet
        
        return total_demand
    
    def _generate_edf_testing_points(self, l_star: int) -> List[int]:
        """
        Generate the testing set for EDF processor demand analysis.
        
        The testing set consists of all absolute deadlines d_{i,k} ≤ L*:
            d_{i,k} = D_i + k·T_i for k = 0, 1, 2, ...
        
        Args:
            l_star: Upper bound of testing interval
            
        Returns:
            Sorted list of unique testing points
        """
        testing_points = set()
        
        for task in self.tasks:
            # Generate deadlines: D_i, D_i + T_i, D_i + 2·T_i, ...
            deadline = task.deadline
            while deadline <= l_star:
                testing_points.add(deadline)
                deadline += task.period
        
        return sorted(testing_points)
    
    def _compute_hyperperiod(self) -> int:
        """Compute hyperperiod (LCM of all periods)."""
        result = self.tasks[0].period
        for task in self.tasks[1:]:
            result = (result * task.period) // math.gcd(result, task.period)
        return result
    
    # =========================================================================
    # Rate Monotonic (RM) Analysis - For reference
    # =========================================================================
    
    def analyze_rm(self) -> DMAnalysisResult:
        """
        Perform Rate Monotonic schedulability analysis using exact RTA.
        
        RM is identical to DM except priority is assigned by period (shorter T = higher priority).
        For implicit deadlines (D_i = T_i), RM and DM produce identical results.
        
        Returns:
            DMAnalysisResult with schedulability verdict and per-task WCRTs
        """
        # Sort tasks by period (RM priority assignment)
        sorted_tasks = sorted(self.tasks, key=lambda t: (t.period, t.id))
        priority_order = [t.id for t in sorted_tasks]
        
        task_results: Dict[int, TaskAnalysisResult] = {}
        all_schedulable = True
        
        for priority, task in enumerate(sorted_tasks):
            hp_tasks = sorted_tasks[:priority]
            wcrt, schedulable = self._compute_wcrt_rta(task, hp_tasks)
            
            result = TaskAnalysisResult(
                task_id=task.id,
                task_name=task.name,
                period=task.period,
                deadline=task.deadline,
                wcet=task.wcet,
                wcrt=wcrt,
                schedulable=schedulable,
                priority=priority
            )
            task_results[task.id] = result
            
            if not schedulable:
                all_schedulable = False
        
        return DMAnalysisResult(
            schedulable=all_schedulable,
            total_utilization=self.total_utilization,
            task_results=task_results,
            priority_order=priority_order
        )
    
    # =========================================================================
    # Utilization Bounds (Sufficient but not Necessary)
    # =========================================================================
    
    def check_liu_layland_bound(self) -> Tuple[bool, float, float]:
        """
        Check Liu & Layland sufficient schedulability bound for RM/DM.
        
        Theorem (Liu & Layland, 1973):
            A set of n periodic tasks is schedulable by RM if:
                U ≤ n(2^{1/n} - 1)
        
        Note: This is a SUFFICIENT condition only. If it fails, the task set
        may still be schedulable (use exact RTA to verify).
        
        Returns:
            Tuple of (passes_bound, utilization, bound_value)
        """
        n = self.n
        bound = n * (2 ** (1/n) - 1)
        passes = self.total_utilization <= bound
        return passes, self.total_utilization, bound
    
    def check_hyperbolic_bound(self) -> Tuple[bool, float]:
        """
        Check Hyperbolic Bound for RM/DM (tighter than Liu-Layland).
        
        Theorem (Bini et al., 2003):
            A set of n periodic tasks is schedulable by RM if:
                Π(U_i + 1) ≤ 2
        
        Returns:
            Tuple of (passes_bound, product_value)
        """
        product = 1.0
        for task in self.tasks:
            product *= (task.utilization + 1)
        passes = product <= 2.0
        return passes, product


# =============================================================================
# Pretty Printing Functions
# =============================================================================

def print_dm_analysis(result: DMAnalysisResult, title: str = "DM Analysis") -> None:
    """Print DM analysis results in a formatted table."""
    print(f"\n{'='*85}")
    print(f" {title}")
    print(f" Algorithm: Deadline Monotonic (DM) with Response Time Analysis (RTA)")
    print(f"{'='*85}")
    print(f" Total Utilization: U = {result.total_utilization:.4f}")
    print(f" Overall Schedulable: {'✓ YES' if result.schedulable else '✗ NO'}")
    print(f"{'='*85}")
    print(f"{'Pri':<5} {'Task':<8} {'T_i':<8} {'D_i':<8} {'C_i':<8} {'R_i':<10} {'R_i≤D_i':<12}")
    print(f"{'-'*85}")
    
    # Print in priority order
    for task_id in result.priority_order:
        r = result.task_results[task_id]
        wcrt_str = str(r.wcrt) if r.wcrt is not None else "N/A"
        status = "✓ Sched" if r.schedulable else "✗ MISS"
        print(f"{r.priority:<5} {r.task_name:<8} {r.period:<8} {r.deadline:<8} "
              f"{r.wcet:<8} {wcrt_str:<10} {status:<12}")
    
    print(f"{'='*85}\n")


def print_edf_analysis(result: EDFAnalysisResult, title: str = "EDF Analysis") -> None:
    """Print EDF analysis results."""
    print(f"\n{'='*85}")
    print(f" {title}")
    print(f" Algorithm: Earliest Deadline First (EDF) with Processor Demand Criterion")
    print(f"{'='*85}")
    print(f" Total Utilization: U = {result.total_utilization:.4f}")
    print(f" Total Density: Δ = {result.total_density:.4f}")
    print(f" Utilization Test (U ≤ 1): {'✓ PASS' if result.utilization_test_passed else '✗ FAIL'}")
    
    if result.l_star is not None:
        print(f" Testing Interval: L* = {result.l_star:.2f}")
    
    if result.critical_point is not None:
        print(f" Critical Point: dbf({result.critical_point}) > {result.critical_point}")
    
    print(f" Overall Schedulable: {'✓ YES' if result.schedulable else '✗ NO'}")
    print(f"{'='*85}\n")


# =============================================================================
# Comparison Function
# =============================================================================

def compare_analyses(dm_result: DMAnalysisResult, edf_result: EDFAnalysisResult) -> None:
    """Print a comparison of DM and EDF analysis results."""
    print(f"\n{'█'*85}")
    print(f" SCHEDULABILITY ANALYSIS COMPARISON")
    print(f"{'█'*85}")
    print(f" Total Utilization: U = {dm_result.total_utilization:.4f}")
    print(f"{'-'*85}")
    print(f" {'Algorithm':<25} {'Schedulable':<15} {'Notes':<40}")
    print(f"{'-'*85}")
    
    dm_status = "✓ YES" if dm_result.schedulable else "✗ NO"
    edf_status = "✓ YES" if edf_result.schedulable else "✗ NO"
    
    dm_notes = "RTA exact analysis"
    if not dm_result.schedulable:
        missed = [r.task_name for r in dm_result.task_results.values() if not r.schedulable]
        dm_notes = f"Tasks missed: {', '.join(missed)}"
    
    edf_notes = "U ≤ 1 sufficient (implicit D)" if edf_result.schedulable else ""
    if edf_result.critical_point:
        edf_notes = f"dbf fails at L={edf_result.critical_point}"
    
    print(f" {'Deadline Monotonic (DM)':<25} {dm_status:<15} {dm_notes:<40}")
    print(f" {'EDF (Processor Demand)':<25} {edf_status:<15} {edf_notes:<40}")
    print(f"{'█'*85}\n")


# =============================================================================
# Main Entry Point for Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    import os
    # Add parent directory to path for direct execution
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import task generator from model.py
    from model import generate_task_sets_by_utilization, print_task_set_table
    
    print("\n" + "█" * 85)
    print(" DRTS Mini-Project Step 2: Analytical Engine Validation")
    print(" Based on Buttazzo's 'Hard Real-Time Computing Systems'")
    print("█" * 85)
    
    # Generate task sets from Step 1
    SEED = 42
    N_TASKS = 5
    
    print(f"\n▶ Using task sets from Step 1 (seed={SEED}, n={N_TASKS})")
    low_u_tasks, high_u_tasks = generate_task_sets_by_utilization(
        n_tasks=N_TASKS,
        period_range=(10, 100),
        seed=SEED
    )
    
    # ==========================================================================
    # Test 1: Low Utilization Task Set (U ≈ 0.5)
    # ==========================================================================
    print("\n" + "▓" * 85)
    print(" TEST 1: LOW UTILIZATION TASK SET (U ≈ 0.5)")
    print("▓" * 85)
    
    print_task_set_table(low_u_tasks, "LOW UTILIZATION TASK SET")
    
    engine_low = AnalyticalEngine(low_u_tasks)
    
    # Liu-Layland Bound Check
    ll_pass, ll_u, ll_bound = engine_low.check_liu_layland_bound()
    print(f"▶ Liu-Layland Bound: U={ll_u:.4f} ≤ {ll_bound:.4f} → {'✓ PASS' if ll_pass else '✗ FAIL'}")
    
    # Hyperbolic Bound Check
    hb_pass, hb_prod = engine_low.check_hyperbolic_bound()
    print(f"▶ Hyperbolic Bound: Π(U_i+1)={hb_prod:.4f} ≤ 2 → {'✓ PASS' if hb_pass else '✗ FAIL'}")
    
    # DM Analysis
    dm_result_low = engine_low.analyze_dm()
    print_dm_analysis(dm_result_low, "DM ANALYSIS - LOW UTILIZATION")
    
    # EDF Analysis  
    edf_result_low = engine_low.analyze_edf()
    print_edf_analysis(edf_result_low, "EDF ANALYSIS - LOW UTILIZATION")
    
    # Comparison
    compare_analyses(dm_result_low, edf_result_low)
    
    # ==========================================================================
    # Test 2: High Utilization Task Set (U ≈ 0.9)
    # ==========================================================================
    print("\n" + "▓" * 85)
    print(" TEST 2: HIGH UTILIZATION TASK SET (U ≈ 0.9)")
    print("▓" * 85)
    
    print_task_set_table(high_u_tasks, "HIGH UTILIZATION TASK SET")
    
    engine_high = AnalyticalEngine(high_u_tasks)
    
    # Liu-Layland Bound Check
    ll_pass, ll_u, ll_bound = engine_high.check_liu_layland_bound()
    print(f"▶ Liu-Layland Bound: U={ll_u:.4f} ≤ {ll_bound:.4f} → {'✓ PASS' if ll_pass else '✗ FAIL'}")
    
    # Hyperbolic Bound Check
    hb_pass, hb_prod = engine_high.check_hyperbolic_bound()
    print(f"▶ Hyperbolic Bound: Π(U_i+1)={hb_prod:.4f} ≤ 2 → {'✓ PASS' if hb_pass else '✗ FAIL'}")
    
    # DM Analysis
    dm_result_high = engine_high.analyze_dm()
    print_dm_analysis(dm_result_high, "DM ANALYSIS - HIGH UTILIZATION")
    
    # EDF Analysis
    edf_result_high = engine_high.analyze_edf()
    print_edf_analysis(edf_result_high, "EDF ANALYSIS - HIGH UTILIZATION")
    
    # Comparison
    compare_analyses(dm_result_high, edf_result_high)
    
    # ==========================================================================
    # Summary
    # ==========================================================================
    print("\n" + "█" * 85)
    print(" STEP 2 SUMMARY")
    print("█" * 85)
    print(f" Low Utilization (U={engine_low.total_utilization:.4f}):")
    print(f"   - DM Schedulable: {'✓ YES' if dm_result_low.schedulable else '✗ NO'}")
    print(f"   - EDF Schedulable: {'✓ YES' if edf_result_low.schedulable else '✗ NO'}")
    print(f" High Utilization (U={engine_high.total_utilization:.4f}):")
    print(f"   - DM Schedulable: {'✓ YES' if dm_result_high.schedulable else '✗ NO'}")
    print(f"   - EDF Schedulable: {'✓ YES' if edf_result_high.schedulable else '✗ NO'}")
    print("█" * 85)
    print(" Step 2 Complete: Analytical Engine ready for simulation comparison")
    print("█" * 85 + "\n")
