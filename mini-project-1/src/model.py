import dataclasses


@dataclasses.dataclass
class Task:
    name: str
    id: int
    bcet: int
    wcet: int
    period: int
    deadline: int
    priority: int = 0  # Lower number = higher priority for RM/DM

    def utilization(self):
        return self.wcet / self.period


@dataclasses.dataclass
class Job:
    task_id: int
    job_id: int
    arrival_time: int
    absolute_deadline: int
    remaining_time: int
    start_time: int = -1
    finish_time: int = -1
    force_finished: bool = False  # True if simulation ends before completion

    @property
    def response_time(self):
        """
        Response time is only meaningful for naturally completed jobs.
        """
        if self.finish_time == -1 or self.force_finished:
            return None
        return self.finish_time - self.arrival_time

    @property
    def is_missed(self):
        """
        A job is considered missed if:
        - it did not complete before simulation ended, or
        - it completed after its absolute deadline.
        """
        if self.force_finished:
            return True
        if self.finish_time == -1:
            return True
        return self.finish_time > self.absolute_deadline
