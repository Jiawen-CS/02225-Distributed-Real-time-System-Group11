from model import Job
import math
import copy
import random
import heapq


class Scheduler:
    def __init__(self, tasks, algorithm="RM", execution_mode="wcet", seed=42):
        """
        execution_mode:
            - "wcet": every job executes exactly WCET
            - "random": execution time sampled uniformly from [BCET, WCET]

        seed:
            used for reproducibility in random mode
        """
        self.tasks = copy.deepcopy(tasks)
        self.algorithm = algorithm
        self.execution_mode = execution_mode
        self.rng = random.Random(seed)
        self.task_map = {}

        self.time = 0
        self.history = []          # (time, task_id)
        self.completed_jobs = []

        periods = [t.period for t in self.tasks]
        self.hyperperiod = math.lcm(*periods) if periods else 0

        # Static priorities for RM / DM
        if algorithm == "RM":
            self.tasks.sort(key=lambda t: (t.period, t.id))
            for i, t in enumerate(self.tasks):
                t.priority = i

        elif algorithm == "DM":
            self.tasks.sort(key=lambda t: (t.deadline, t.id))
            for i, t in enumerate(self.tasks):
                t.priority = i

        elif algorithm == "EDF":
            pass
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        self.task_map = {t.id: t for t in self.tasks}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_exec_time(self, task):
        """
        In discrete-time simulation, execution time must be at least 1.
        This avoids jobs with 0 execution that would never complete correctly.
        """
        if self.execution_mode == "wcet":
            return task.wcet
        elif self.execution_mode == "random":
            low = min(task.bcet, task.wcet)
            high = max(task.bcet, task.wcet)
            return max(1, self.rng.randint(low, high))
        else:
            raise ValueError(f"Unknown execution_mode: {self.execution_mode}")

    def _job_priority(self, job):
        if self.algorithm in ["RM", "DM"]:
            return (
                self.task_map[job.task_id].priority,
                job.arrival_time,
                job.task_id,
                job.job_id,
            )

        if self.algorithm == "EDF":
            return (
                job.absolute_deadline,
                job.arrival_time,
                job.task_id,
                job.job_id,
            )

        raise ValueError(f"Unknown algorithm: {self.algorithm}")

    def get_task(self, task_id):
        try:
            return self.task_map[task_id]
        except KeyError as exc:
            raise ValueError(f"Task with ID {task_id} not found.") from exc

    # ------------------------------------------------------------------
    # Main simulation
    # ------------------------------------------------------------------

    def run(self, duration=None, record_history=True):
        if duration is None:
            duration = self.hyperperiod

        print(
            f"--- Running {self.algorithm} simulation "
            f"({self.execution_mode}) for {duration} cycles ---"
        )

        self.time = 0
        self.history = []
        self.completed_jobs = []

        release_buckets = {}
        for task in self.tasks:
            job_id = 0
            while job_id * task.period < duration:
                release_time = job_id * task.period
                exec_time = self._get_exec_time(task)
                release_buckets.setdefault(release_time, []).append(
                    Job(
                        task_id=task.id,
                        job_id=job_id,
                        arrival_time=release_time,
                        absolute_deadline=release_time + task.deadline,
                        remaining_time=exec_time,
                    )
                )
                job_id += 1

        ready_heap = []

        for t in range(duration):
            self.time = t

            # Release new jobs
            for job in release_buckets.get(t, []):
                heapq.heappush(ready_heap, (self._job_priority(job), job))

            # Execute one time unit
            if ready_heap:
                _, current_job = heapq.heappop(ready_heap)

                if current_job.start_time == -1:
                    current_job.start_time = t

                if record_history:
                    self.history.append((t, current_job.task_id))
                current_job.remaining_time -= 1

                if current_job.remaining_time == 0:
                    current_job.finish_time = t + 1
                    current_job.force_finished = False
                    self.completed_jobs.append(current_job)
                else:
                    heapq.heappush(ready_heap, (self._job_priority(current_job), current_job))
            else:
                if record_history:
                    self.history.append((t, None))

        # Jobs still unfinished at simulation end
        for _, job in ready_heap:
            job.force_finished = True
            job.finish_time = -1
            self.completed_jobs.append(job)
        return self.completed_jobs, self.history

    # ------------------------------------------------------------------
    # Result analysis
    # ------------------------------------------------------------------

    def analyze_results(self):
        """
        Returns per-task statistics:
            - Sim_WCRT: worst observed response time among naturally completed jobs
            - Sim_Avg_RT: average response time among naturally completed jobs
            - Missed: number of missed / unfinished jobs
        """
        stats = {}

        for task in self.tasks:
            jobs = [j for j in self.completed_jobs if j.task_id == task.id]

            natural_jobs = [j for j in jobs if not j.force_finished]
            valid_rts = [j.response_time for j in natural_jobs if j.response_time is not None]

            sim_wcrt = max(valid_rts) if valid_rts else 0
            sim_avg = sum(valid_rts) / len(valid_rts) if valid_rts else 0
            missed = sum(1 for j in jobs if j.is_missed)

            stats[task.id] = {
                "Sim_WCRT": sim_wcrt,
                "Sim_Avg_RT": sim_avg,
                "Missed": missed,
            }

        return stats
