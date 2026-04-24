class CreditBasedShaper:
    def __init__(self, idle_slope, send_slope):
        self.credit = 0.0
        self.idle_slope = idle_slope # bits per microsecond
        self.send_slope = send_slope # bits per microsecond (negative)
        self.last_update_time = 0.0

class PortScheduler:
    def __init__(self, bandwidth_mbps, mode='SP', reservations=None):
        self.bandwidth_mbps = bandwidth_mbps
        self.mode = mode
        # 8 Priority Queues
        self.queues = {i: [] for i in range(8)}
        self.busy_until = 0.0
        self.current_tx_priority = None
        
        # CBS shapers are keyed by PCP in this project setup.
        self.shapers = {}
        if self.mode == 'CBS' and reservations:
            for prio, bw_fraction in reservations.items():
                link_bw = self.bandwidth_mbps 
                idle_slope = link_bw * bw_fraction
                send_slope = idle_slope - link_bw
                self.shapers[prio] = CreditBasedShaper(idle_slope, send_slope)

    def advance_time(self, current_time):
        for prio, shaper in self.shapers.items():
            time_delta = current_time - shaper.last_update_time
            if time_delta <= 0:
                continue

            if self.current_tx_priority == prio:
                shaper.credit += shaper.send_slope * time_delta
            elif self.queues[prio]:
                # A backlogged AVB queue earns credit while waiting.
                shaper.credit += shaper.idle_slope * time_delta
            elif shaper.credit > 0:
                # Positive credit is cleared when the queue is idle.
                shaper.credit = 0.0

            shaper.last_update_time = current_time

    def enqueue(self, frame, current_time):
        self.advance_time(current_time)
        self.queues[frame.priority].append(frame)

    def get_next_frame(self, current_time):
        self.advance_time(current_time)
        if current_time < self.busy_until:
            return None, -1

        for p in range(7, -1, -1):
            if self.queues[p]:
                if self.mode == 'CBS' and p in self.shapers:
                    shaper = self.shapers[p]
                    if shaper.credit >= 0:
                        frame = self.queues[p].pop(0)
                        return frame, p
                    continue
                else:
                    return self.queues[p].pop(0), p

        return None, -1

    def next_eligible_time(self, current_time):
        self.advance_time(current_time)
        next_time = None

        for p in range(7, -1, -1):
            if not self.queues[p] or p not in self.shapers:
                continue

            shaper = self.shapers[p]
            if shaper.credit >= 0:
                return current_time

            if shaper.idle_slope > 0:
                eligible_time = current_time + ((-shaper.credit) / shaper.idle_slope)
                if next_time is None or eligible_time < next_time:
                    next_time = eligible_time

        return next_time

    def transmission_time(self, frame_size_bytes):
        return (frame_size_bytes * 8.0) / self.bandwidth_mbps

    def on_transmission_start(self, priority, current_time, duration):
        self.advance_time(current_time)
        self.current_tx_priority = priority
        self.busy_until = current_time + duration

    def on_transmission_end(self, current_time):
        self.advance_time(current_time)
        self.current_tx_priority = None
        self.busy_until = current_time

        for prio, shaper in self.shapers.items():
            if not self.queues[prio] and shaper.credit > 0:
                shaper.credit = 0.0
