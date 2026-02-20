from model import Task, Job
import math
import copy

class Scheduler:
    def __init__(self, tasks, algorithm="RM"):
        # Use deepcopy to prevent modifying the original task list/objects (e.g. priorities)
        self.tasks = copy.deepcopy(tasks)
        self.algorithm = algorithm
        self.time = 0
        self.ready_queue = []
        self.history = [] # For Gantt chart
        self.completed_jobs = []
        
        # Determine hyperperiod (LCM) to know how long to run
        periods = [t.period for t in self.tasks]
        self.hyperperiod = math.lcm(*periods) if periods else 0
        
        # Pre-assign static priorities for RM
        # if algorithm == "RM":
        #     # Sort tasks by period (shortest period first)
        #     self.tasks.sort(key=lambda t: t.period)
        #     for i, t in enumerate(self.tasks):
        #         t.priority = i
        if algorithm == "DM":
            # Sort tasks by deadline (shortest deadline first)
            self.tasks.sort(key=lambda t: t.deadline)
            for i, t in enumerate(self.tasks):
                t.priority = i

    def _get_active_job(self):
        if not self.ready_queue:
            return None
        
        if self.algorithm in ["RM", "DM"]:
            # Filter queue for ready jobs, sort by static priority
            return min(self.ready_queue, key=lambda j: self.get_task(j.task_id).priority)
        
        elif self.algorithm == "EDF":
            # Sort by absolute deadline
            return min(self.ready_queue, key=lambda j: j.absolute_deadline)
        return None

    def get_task(self, task_id):
        # Optimized lookup or safe lookup
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise ValueError(f"Task with ID {task_id} not found in scheduler.")

    def run(self, duration=None):
        if duration is None:
            duration = self.hyperperiod

        print(f"--- Running {self.algorithm} Simulation for {duration} cycles ---")

        current_job = None
        
        for t in range(duration):
            self.time = t
            
            # 1. Check for Task Arrivals (Releases)
            for task in self.tasks:
                if t % task.period == 0:
                    new_job = Job(
                        task_id=task.id,
                        job_id=int(t / task.period),
                        arrival_time=t,
                        absolute_deadline=t + task.deadline,
                        remaining_time=task.wcet
                    )
                    self.ready_queue.append(new_job)

            # 2. Scheduling Decision
            next_job = self._get_active_job()

            # 3. Context Switch / Preemption Logic
            if next_job != current_job:
                # Logic to handle logging if needed
                if next_job is not None and next_job.start_time == -1:
                    next_job.start_time = t
                current_job = next_job

            # 4. Execution
            if current_job:
                self.history.append((t, current_job.task_id))
                current_job.remaining_time -= 1
                
                # 5. Job Completion
                if current_job.remaining_time == 0:
                    current_job.finish_time = t + 1
                    self.completed_jobs.append(current_job)
                    self.ready_queue.remove(current_job)
                    current_job = None
            else:
                self.history.append((t, None)) # Idle

        return self.completed_jobs, self.history

    def analyze_results(self):
        stats = {}
        for task in self.tasks:
            jobs = [j for j in self.completed_jobs if j.task_id == task.id]
            if not jobs:
                stats[task.id] = {
                    "Sim_WCRT": 0,
                    "Sim_Avg_RT": 0,
                    "Missed": 0
                }
                continue
            
            # Calculate Worst Case Response Time observed in Sim
            max_response = max(j.response_time for j in jobs)
            avg_response = sum(j.response_time for j in jobs) / len(jobs)
            missed_deadlines = sum(1 for j in jobs if j.is_missed)
            
            stats[task.id] = {
                "Sim_WCRT": max_response,
                "Sim_Avg_RT": avg_response,
                "Missed": missed_deadlines
            }
        return stats