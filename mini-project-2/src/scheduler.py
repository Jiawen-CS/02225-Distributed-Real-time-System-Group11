class CreditBasedShaper:
    def __init__(self, idle_slope, send_slope):
        self.credit = 0.0
        self.idle_slope = idle_slope # bits per microsecond
        self.send_slope = send_slope # bits per microsecond (negative)
        self.last_update_time = 0.0
        
    def update_credit(self, current_time, is_transmitting):
        time_delta = current_time - self.last_update_time
        if time_delta <= 0:
            return

        if is_transmitting:
            self.credit += self.send_slope * time_delta
        else:
            # If queue is not empty (implied if we are calling this while waiting), credit increases
            self.credit += self.idle_slope * time_delta
            
        self.last_update_time = current_time

    def reset_credit(self, current_time):
        # When queue becomes empty, if credit is positive, set to 0. 
        # If negative, it must grow back to 0 (handled by update_credit logic if we consider 'waiting' correctly, 
        # but simplified: if empty, we usually reset positive credit immediately).
        # For exact behavior: "If the queue is empty, and credit is positive, set to 0."
        # "If queue is empty and credit is negative, it increases at idleSlope until 0."
        # We will handle this in the scheduler loop.
        self.last_update_time = current_time
        if self.credit > 0:
            self.credit = 0.0

class PortScheduler:
    def __init__(self, bandwidth_mbps, mode='SP', reservations=None):
        self.bandwidth_mbps = bandwidth_mbps
        self.mode = mode
        # 8 Priority Queues
        self.queues = {i: [] for i in range(8)}
        self.busy_until = 0.0
        
        # CBS Shapers for Class A (Prio 3) and Class B (Prio 2)
        self.shapers = {}
        if self.mode == 'CBS' and reservations:
            for prio, bw_fraction in reservations.items():
                # bandwidth is in Mbps = bits/us
                link_bw = self.bandwidth_mbps 
                idle_slope = link_bw * bw_fraction
                send_slope = idle_slope - link_bw
                self.shapers[prio] = CreditBasedShaper(idle_slope, send_slope)

    def enqueue(self, frame):
        self.queues[frame.priority].append(frame)

    def get_next_frame(self, current_time):
        if current_time < self.busy_until:
            return None
            
        # Update credits for CBS queues up to current_time
        # Note: This is a simplification. In a real event-driven sim, we need to update credit 
        # continuously or at events. Here we update when we check for frames.
        # We need to know if the queue was empty or not to update correctly. 
        # This simple update might be insufficient for exact CBS behavior without tracking queue empty times.
        # However, for a basic simulator, we assume credit behaves correctly between events.
        
        # Strict Priority / CBS Selection
        # Priorities: 7 down to 0.
        # If CBS is enabled for a priority, check credit.
        
        for p in range(7, -1, -1):
            if self.queues[p]:
                # Check CBS eligibility
                if self.mode == 'CBS' and p in self.shapers:
                    shaper = self.shapers[p]
                    # Update credit based on waiting time since last update
                    # Assumption: Queue has been non-empty since last check? 
                    # Not necessarily. This is tricky in pure event driven without queue-state events.
                    # We will do a best-effort update:
                    # If we are here, queue is not empty. 
                    # We assume it was waiting since last_update_time.
                    shaper.update_credit(current_time, is_transmitting=False)
                    
                    if shaper.credit >= 0:
                        pkt = self.queues[p].pop(0)
                        return pkt, p # Return frame and priority to handle credit update after transmission
                    else:
                        # Credit negative, cannot transmit. 
                        # In pure CBS, we might wait. In SP+CBS, we check lower priorities?
                        # IEEE 802.1Qav: If credit < 0, cannot transmit. 
                        # Lower priorities can transmit if higher are blocked by credit.
                        continue 
                else:
                    # Strict Priority (or non-CBS queue)
                    return self.queues[p].pop(0), p
        
        # If no frame found (or all CBS blocked)
        # We need to update credits for empty queues too (reset positive to 0, negative grows)
        if self.mode == 'CBS':
            for p, shaper in self.shapers.items():
                if not self.queues[p]:
                    # Queue empty
                    # If credit > 0, reset to 0. If < 0, increase.
                    # We simulate this by updating as if waiting, then clamping.
                    shaper.update_credit(current_time, is_transmitting=False)
                    if shaper.credit > 0:
                        shaper.credit = 0.0
                        
        return None, -1
    
    def transmission_time(self, frame_size_bytes):
        # size (bytes) * 8 / (bandwidth (Mbps) * 10^6) * 10^6 (us)
        # = size * 8 / bandwidth
        return (frame_size_bytes * 8.0) / self.bandwidth_mbps

    def on_transmission_start(self, priority, frame_size, current_time):
        # Called when a frame starts transmission
        if self.mode == 'CBS' and priority in self.shapers:
            shaper = self.shapers[priority]
            # Credit is already updated to current_time in get_next_frame
            # We need to deduct credit for the transmission duration
            # But credit decreases *during* transmission. 
            # The standard says: credit -= sendSlope * transmissionTime
            # We can apply this immediately or at end. 
            # Let's apply immediately for the next check.
            duration = self.transmission_time(frame_size)
            # update_credit adds (send_slope * duration)
            # We manually adjust credit
            shaper.credit += shaper.send_slope * duration
            shaper.last_update_time = current_time + duration

