import dataclasses

@dataclasses.dataclass
class Task:
    name: str
    id: int # split from the task name
    bcet: int  # Best Case Execution Time
    wcet: int      # Worst Case Execution Time (Ci)
    period: int   # Period (Ti)
    deadline: int  # Relative Deadline (Di)
    priority: int # Lower number = Higher priority (for RM)

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
    
    @property
    def response_time(self):
        if self.finish_time == -1:
            return None
        return self.finish_time - self.arrival_time
    
    @property
    def is_missed(self):
        if self.finish_time == -1:
            return False # Not finished yet
        return self.finish_time > self.absolute_deadline