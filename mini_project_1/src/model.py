"""
model.py - Task Model Definition for Real-Time Systems

Based on Buttazzo's "Hard Real-Time Computing Systems" textbook.
A periodic task τ_i is characterized by:
  - T_i: Period (inter-arrival time)
  - D_i: Relative Deadline (D_i ≤ T_i for constrained deadlines)
  - C_i: Worst-Case Execution Time (WCET)
  - C_i^-: Best-Case Execution Time (BCET)
  - Φ_i: Phase (initial offset/release time of first job)
"""

import dataclasses
from typing import Optional


@dataclasses.dataclass
class Task:
    """
    Represents a periodic real-time task τ_i.
    
    Notation follows Buttazzo's textbook:
      - period (T_i): The minimum inter-arrival time between consecutive jobs
      - deadline (D_i): Relative deadline, where D_i ≤ T_i (constrained deadline model)
      - wcet (C_i): Worst-Case Execution Time
      - bcet (C_i^-): Best-Case Execution Time, where BCET ≤ WCET
      - phase (Φ_i): Initial offset (release time of first job)
    """
    id: int                          # Unique task identifier
    period: int                      # T_i: Period (must be > 0)
    deadline: int                    # D_i: Relative deadline (0 < D_i ≤ T_i)
    wcet: int                        # C_i: Worst-Case Execution Time (must be > 0)
    bcet: int = 0                    # C_i^-: Best-Case Execution Time (0 ≤ BCET ≤ WCET)
    phase: int = 0                   # Φ_i: Phase/Offset (≥ 0)
    name: Optional[str] = None       # Human-readable name (optional)
    priority: Optional[int] = None   # Static priority (assigned by scheduler, not intrinsic)

    def __post_init__(self):
        """Validate task parameters according to real-time systems theory."""
        # Auto-generate name if not provided
        if self.name is None:
            self.name = f"τ_{self.id}"
        
        # Validate constraints
        if self.period <= 0:
            raise ValueError(f"Task {self.name}: Period T_i must be positive (got {self.period})")
        if self.wcet <= 0:
            raise ValueError(f"Task {self.name}: WCET C_i must be positive (got {self.wcet})")
        if self.deadline <= 0 or self.deadline > self.period:
            raise ValueError(f"Task {self.name}: Deadline D_i must satisfy 0 < D_i ≤ T_i "
                           f"(got D={self.deadline}, T={self.period})")
        if self.bcet < 0 or self.bcet > self.wcet:
            raise ValueError(f"Task {self.name}: BCET must satisfy 0 ≤ BCET ≤ WCET "
                           f"(got BCET={self.bcet}, WCET={self.wcet})")
        if self.phase < 0:
            raise ValueError(f"Task {self.name}: Phase Φ_i must be non-negative (got {self.phase})")
        if self.wcet > self.deadline:
            raise ValueError(f"Task {self.name}: WCET must not exceed deadline "
                           f"(got C={self.wcet}, D={self.deadline})")

    @property
    def utilization(self) -> float:
        """
        Calculate task utilization U_i = C_i / T_i.
        
        This represents the fraction of processor time required by this task.
        """
        return self.wcet / self.period

    @property
    def density(self) -> float:
        """
        Calculate task density δ_i = C_i / min(D_i, T_i).
        
        For constrained deadlines (D_i ≤ T_i), density = C_i / D_i.
        Density is a tighter bound than utilization when D_i < T_i.
        """
        return self.wcet / min(self.deadline, self.period)

    def __repr__(self) -> str:
        return (f"Task(id={self.id}, T={self.period}, D={self.deadline}, "
                f"C={self.wcet}, BCET={self.bcet}, Φ={self.phase})")

@dataclasses.dataclass
class Job:
    """
    Represents a job (instance) of a periodic task.
    
    Job j_{i,k} is the k-th instance of task τ_i, released at time r_{i,k} = Φ_i + k*T_i
    with absolute deadline d_{i,k} = r_{i,k} + D_i.
    """
    task_id: int
    job_id: int
    arrival_time: int
    absolute_deadline: int
    remaining_time: int
    start_time: int = -1
    finish_time: int = -1
    
    @property
    def response_time(self) -> Optional[int]:
        """Response time R = finish_time - arrival_time."""
        if self.finish_time == -1:
            return None
        return self.finish_time - self.arrival_time
    
    @property
    def is_missed(self) -> bool:
        """Check if this job missed its deadline."""
        if self.finish_time == -1:
            return False  # Not finished yet
        return self.finish_time > self.absolute_deadline


# =============================================================================
# Task Set Generator (UUniFast Algorithm)
# =============================================================================

import random
import math
from typing import List, Tuple


def uunifast(n: int, u_total: float, seed: Optional[int] = None) -> List[float]:
    """
    UUniFast algorithm for generating unbiased random utilization values.
    
    From: Bini & Buttazzo, "Measuring the Performance of Schedulability Tests" (2005)
    
    This algorithm generates n utilization values that sum to u_total,
    with a uniform distribution over the space of valid utilization vectors.
    
    Args:
        n: Number of tasks
        u_total: Target total utilization (0 < u_total ≤ n)
        seed: Random seed for reproducibility
        
    Returns:
        List of n utilization values that sum to u_total
    """
    if seed is not None:
        random.seed(seed)
    
    utilizations = []
    sum_u = u_total
    
    for i in range(1, n):
        # Generate next utilization using UUniFast formula
        next_sum_u = sum_u * (random.random() ** (1.0 / (n - i)))
        utilizations.append(sum_u - next_sum_u)
        sum_u = next_sum_u
    
    utilizations.append(sum_u)  # Last task gets remaining utilization
    
    return utilizations


def generate_task_set(
    n_tasks: int,
    target_utilization: float,
    period_range: Tuple[int, int] = (10, 100),
    deadline_factor_range: Tuple[float, float] = (0.8, 1.0),
    bcet_factor_range: Tuple[float, float] = (0.3, 0.8),
    use_harmonic_periods: bool = False,
    seed: Optional[int] = None
) -> List[Task]:
    """
    Generate a random task set with specified total utilization.
    
    Uses the UUniFast algorithm for unbiased utilization distribution,
    following best practices from real-time systems literature.
    
    Args:
        n_tasks: Number of tasks to generate
        target_utilization: Target total utilization U (0 < U ≤ 1 for schedulability)
        period_range: (min_period, max_period) tuple
        deadline_factor_range: (min_factor, max_factor) where D_i = factor * T_i
                               factor ∈ (0, 1] ensures D_i ≤ T_i
        bcet_factor_range: (min_factor, max_factor) where BCET = factor * WCET
        use_harmonic_periods: If True, use harmonic periods (powers of 2)
        seed: Random seed for reproducibility
        
    Returns:
        List of Task objects
        
    Raises:
        ValueError: If parameters are invalid or task generation fails
    """
    if seed is not None:
        random.seed(seed)
    
    if target_utilization <= 0:
        raise ValueError("Target utilization must be positive")
    if n_tasks <= 0:
        raise ValueError("Number of tasks must be positive")
    
    # Step 1: Generate utilization values using UUniFast
    utilizations = uunifast(n_tasks, target_utilization, seed)
    
    # Step 2: Generate periods
    min_period, max_period = period_range
    if use_harmonic_periods:
        # Generate harmonic periods (powers of 2)
        min_exp = max(1, int(math.log2(min_period)))
        max_exp = int(math.log2(max_period))
        periods = [2 ** random.randint(min_exp, max_exp) for _ in range(n_tasks)]
    else:
        # Generate random periods
        periods = [random.randint(min_period, max_period) for _ in range(n_tasks)]
    
    # Step 3: Create tasks
    tasks = []
    for i in range(n_tasks):
        period = periods[i]
        u_i = utilizations[i]
        
        # Calculate WCET from utilization: C_i = U_i * T_i
        wcet = max(1, int(round(u_i * period)))
        
        # Generate relative deadline: D_i ≤ T_i (constrained deadline model)
        min_d_factor, max_d_factor = deadline_factor_range
        d_factor = random.uniform(min_d_factor, max_d_factor)
        deadline = max(wcet, int(round(d_factor * period)))  # Ensure D_i ≥ C_i
        deadline = min(deadline, period)  # Ensure D_i ≤ T_i
        
        # Generate BCET: BCET ≤ WCET
        min_b_factor, max_b_factor = bcet_factor_range
        b_factor = random.uniform(min_b_factor, max_b_factor)
        bcet = max(1, int(round(b_factor * wcet)))
        
        # Phase is 0 for synchronous task sets (standard assumption)
        phase = 0
        
        task = Task(
            id=i,
            period=period,
            deadline=deadline,
            wcet=wcet,
            bcet=bcet,
            phase=phase
        )
        tasks.append(task)
    
    return tasks


def generate_task_sets_by_utilization(
    n_tasks: int = 5,
    period_range: Tuple[int, int] = (10, 100),
    seed: Optional[int] = None
) -> Tuple[List[Task], List[Task]]:
    """
    Generate two task sets: one with low utilization and one with high utilization.
    
    Args:
        n_tasks: Number of tasks per set
        period_range: (min_period, max_period) tuple
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (low_utilization_tasks, high_utilization_tasks)
        - Low utilization: U ≈ 0.5 (easily schedulable)
        - High utilization: U ≈ 0.9 (challenging but typically schedulable)
    """
    # Low utilization task set (U ≈ 0.5)
    low_u_seed = seed if seed is None else seed
    low_u_tasks = generate_task_set(
        n_tasks=n_tasks,
        target_utilization=0.5,
        period_range=period_range,
        deadline_factor_range=(0.9, 1.0),  # D_i close to T_i
        seed=low_u_seed
    )
    
    # High utilization task set (U ≈ 0.9)
    high_u_seed = None if seed is None else seed + 1000
    high_u_tasks = generate_task_set(
        n_tasks=n_tasks,
        target_utilization=0.9,
        period_range=period_range,
        deadline_factor_range=(0.9, 1.0),  # D_i close to T_i
        seed=high_u_seed
    )
    
    return low_u_tasks, high_u_tasks


def print_task_set_table(tasks: List[Task], title: str = "Task Set") -> None:
    """
    Print a task set in a formatted table.
    
    Displays all task parameters including calculated utilization and density.
    """
    total_u = sum(t.utilization for t in tasks)
    total_density = sum(t.density for t in tasks)
    
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f" Total Utilization: U = {total_u:.4f}")
    print(f" Total Density: Δ = {total_density:.4f}")
    print(f"{'='*80}")
    print(f"{'Task':<8} {'Period':<10} {'Deadline':<10} {'WCET':<8} {'BCET':<8} "
          f"{'Phase':<8} {'U_i':<10} {'δ_i':<10}")
    print(f"{'-'*80}")
    
    for task in sorted(tasks, key=lambda t: t.id):
        print(f"{task.name:<8} {task.period:<10} {task.deadline:<10} {task.wcet:<8} "
              f"{task.bcet:<8} {task.phase:<8} {task.utilization:<10.4f} {task.density:<10.4f}")
    
    print(f"{'-'*80}")
    print(f"{'TOTAL':<8} {'':<10} {'':<10} {'':<8} {'':<8} {'':<8} "
          f"{total_u:<10.4f} {total_density:<10.4f}")
    print(f"{'='*80}\n")


# =============================================================================
# Main entry point for testing
# =============================================================================

if __name__ == "__main__":
    print("\n" + "█" * 80)
    print(" DRTS Mini-Project Step 1: Task Model & Generator Validation")
    print(" Based on Buttazzo's 'Hard Real-Time Computing Systems'")
    print("█" * 80)
    
    # Generate task sets with fixed seed for reproducibility
    SEED = 42
    N_TASKS = 5
    
    print(f"\n▶ Generating {N_TASKS} tasks per set with seed={SEED}")
    print("  - Low utilization target: U ≈ 0.5")
    print("  - High utilization target: U ≈ 0.9")
    
    low_u_tasks, high_u_tasks = generate_task_sets_by_utilization(
        n_tasks=N_TASKS,
        period_range=(10, 100),
        seed=SEED
    )
    
    # Print task sets
    print_task_set_table(low_u_tasks, "LOW UTILIZATION TASK SET (U ≈ 0.5)")
    print_task_set_table(high_u_tasks, "HIGH UTILIZATION TASK SET (U ≈ 0.9)")
    
    # Validation checks
    print("\n▶ Validation Checks:")
    print("-" * 40)
    
    for name, tasks in [("Low U", low_u_tasks), ("High U", high_u_tasks)]:
        all_valid = True
        for t in tasks:
            # Check D_i ≤ T_i
            if t.deadline > t.period:
                print(f"  ✗ {name} {t.name}: D > T (INVALID)")
                all_valid = False
            # Check C_i ≤ D_i
            if t.wcet > t.deadline:
                print(f"  ✗ {name} {t.name}: C > D (INVALID)")
                all_valid = False
            # Check BCET ≤ WCET
            if t.bcet > t.wcet:
                print(f"  ✗ {name} {t.name}: BCET > WCET (INVALID)")
                all_valid = False
        
        if all_valid:
            total_u = sum(t.utilization for t in tasks)
            print(f"  ✓ {name} Task Set: All constraints satisfied (U = {total_u:.4f})")
    
    print("\n" + "█" * 80)
    print(" Step 1 Complete: Task model and generator ready for analysis")
    print("█" * 80 + "\n")