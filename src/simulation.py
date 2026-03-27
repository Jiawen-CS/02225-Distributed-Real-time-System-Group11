# simulation.py
from model import Job
import math
import copy
import random


class Scheduler:
    def __init__(self, tasks, algorithm="RM"):
        # Deep-copy to avoid mutating the original task objects (e.g. priority fields)
        self.tasks = copy.deepcopy(tasks)
        self.algorithm = algorithm
        self.time = 0
        self.ready_queue = []
        self.history = []           # (time, task_id) pairs used for Gantt chart
        self.completed_jobs = []

        # Hyperperiod = LCM of all periods -> simulation length
        periods = [t.period for t in self.tasks]
        self.hyperperiod = math.lcm(*periods) if periods else 0

        # Assign static priorities based on algorithm
        if algorithm == "RM":
            # Rate Monotonic: shorter period -> higher priority (lower number)
            self.tasks.sort(key=lambda t: (t.period, t.id))
            for i, t in enumerate(self.tasks):
                t.priority = i

        elif algorithm == "DM":
            # Deadline Monotonic: shorter relative deadline -> higher priority
            self.tasks.sort(key=lambda t: (t.deadline, t.id))
            for i, t in enumerate(self.tasks):
                t.priority = i

        # EDF has no static priority; scheduling decision is made dynamically

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_active_job(self):
        """Return the highest-priority ready job according to the algorithm."""
        if not self.ready_queue:
            return None

        if self.algorithm in ["RM", "DM"]:
            # Static priority: lowest number wins
            return min(self.ready_queue,
                       key=lambda j: self.get_task(j.task_id).priority)

        elif self.algorithm == "EDF":
            # Dynamic priority: earliest absolute deadline wins
            return min(self.ready_queue,
                       key=lambda j: (j.absolute_deadline, j.arrival_time))

        return None

    def get_task(self, task_id):
        """Look up a Task object by its ID."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise ValueError(f"Task with ID {task_id} not found in scheduler.")

    # ------------------------------------------------------------------
    # Main simulation loop
    # ------------------------------------------------------------------

    def run(self, duration=None):
        if duration is None:
            duration = self.hyperperiod

        print(f"--- Running {self.algorithm} Simulation for {duration} cycles ---")

        current_job = None

        for t in range(duration):
            self.time = t

            # 1. Release new jobs at each task's period boundary
            for task in self.tasks:
                if t % task.period == 0:
                    # Sample execution time uniformly in [BCET, WCET].
                    # Use max(1, ...) to guarantee at least 1 cycle of work,
                    # preventing zero-execution jobs that never complete.
                    # exec_time = max(1, random.randint(task.bcet, task.wcet))
                    exec_time = task.wcet  # For worst-case load testing, use WCET directly
                    new_job = Job(
                        task_id=task.id,
                        job_id=int(t / task.period),
                        arrival_time=t,
                        absolute_deadline=t + task.deadline,
                        remaining_time=exec_time
                    )
                    self.ready_queue.append(new_job)

            # 2. Select the next job to run
            next_job = self._get_active_job()

            # 3. Handle context switch / preemption
            if next_job != current_job:
                if next_job is not None and next_job.start_time == -1:
                    next_job.start_time = t
                current_job = next_job

            # 4. Execute for one time unit
            if current_job:
                self.history.append((t, current_job.task_id))
                current_job.remaining_time -= 1

                # 5. Job completion check
                if current_job.remaining_time == 0:
                    current_job.finish_time = t + 1
                    current_job.force_finished = False  # Completed naturally
                    self.completed_jobs.append(current_job)
                    self.ready_queue.remove(current_job)
                    current_job = None
            else:
                self.history.append((t, None))  # CPU idle

        # 6. Handle jobs still in the queue at end of simulation (deadline misses)
        # Mark them as force-finished so they are excluded from WCRT calculation
        # but still counted as missed deadlines
        for job in self.ready_queue:
            # job.finish_time = duration
            job.force_finished = True   # Did not finish naturally
            self.completed_jobs.append(job)
        self.ready_queue.clear()

        return self.completed_jobs, self.history

    # ------------------------------------------------------------------
    # Result analysis
    # ------------------------------------------------------------------

    def analyze_results(self):
        """
        Compute per-task statistics from completed jobs:
          - Sim_WCRT   : worst observed response time among naturally completed jobs
          - Sim_Avg_RT : average response time among naturally completed jobs
          - Missed     : number of jobs that exceeded their absolute deadline
        
        Jobs that were force-finished at simulation end are excluded from
        WCRT/Avg_RT (their response time is meaningless), but are still
        counted as missed deadlines.
        """
        stats = {}
        for task in self.tasks:
            jobs = [j for j in self.completed_jobs if j.task_id == task.id]
            if not jobs:
                stats[task.id] = {"Sim_WCRT": 0, "Sim_Avg_RT": 0, "Missed": 0}
                continue

            # Only use naturally completed jobs for response time statistics
            natural_jobs = [j for j in jobs if not j.force_finished]
            valid_rts = [j.response_time for j in natural_jobs
                         if j.response_time is not None]

            max_response = max(valid_rts) if valid_rts else 0
            avg_response = sum(valid_rts) / len(valid_rts) if valid_rts else 0

            # All jobs (including force-finished) count toward missed deadlines
            missed = sum(1 for j in jobs if j.is_missed)

            stats[task.id] = {
                "Sim_WCRT":   max_response,
                "Sim_Avg_RT": avg_response,
                "Missed":     missed,
            }
        return stats