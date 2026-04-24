import heapq
from .model import Frame
from .scheduler import PortScheduler

class Event:
    def __init__(self, time, type, frame, node_id):
        self.time = time
        self.type = type # GENERATION, ARRIVAL, DEPARTURE
        self.frame = frame
        self.node_id = node_id
        
    def __lt__(self, other):
        return self.time < other.time

class Simulator:
    def __init__(self, nodes, links, streams, routes, mode='CBS'):
        self.nodes = nodes
        self.links = links
        self.streams = streams
        self.routes = routes
        self.events = []
        self.current_time = 0.0
        self.port_schedulers = {}
        self.latencies = {s.id: [] for s in streams}
        
        # Map: (node_id, port_id) -> {priority: bandwidth_fraction}
        reservations = {}
        
        for stream in streams:
            if stream.id not in routes:
                continue
            route = routes[stream.id]

            for hop in route.path:
                node_id = hop['node']
                port_id = hop['port']
                
                if node_id in nodes and port_id in nodes[node_id].outgoing_links:
                    if (node_id, port_id) not in reservations:
                        reservations[(node_id, port_id)] = {}
                    
                    if stream.pcp in (1, 2):
                        reservations[(node_id, port_id)][stream.pcp] = 0.5

        for port_key, res in reservations.items():
            res.setdefault(2, 0.0)
            res.setdefault(1, 0.0)

        for node_id, node in nodes.items():
            for port, link in node.outgoing_links.items():
                port_res = reservations.get((node_id, port), {})
                self.port_schedulers[(node_id, port)] = PortScheduler(
                    link.bandwidth_mbps, 
                    mode=mode, 
                    reservations=port_res
                )

    def schedule_event(self, event):
        heapq.heappush(self.events, event)

    def run(self, duration):
        # Schedule initial generations
        for stream in self.streams:
            t = 0.0
            frame_count = 0
            while t < duration:
                frame = Frame(frame_count, stream.id, stream.size, t, stream.pcp)
                self.schedule_event(Event(t, "GENERATION", frame, stream.source))
                t += stream.period
                frame_count += 1
        
        # Keep running, process events
        while self.events:
            event = heapq.heappop(self.events)
            if event.time > duration:
                break
            
            self.current_time = event.time
            
            if event.type == "GENERATION":
                self.handle_arrival(event) # Generation is essentially arrival at source
            elif event.type == "ARRIVAL":
                self.handle_arrival(event)
            elif event.type == "DEPARTURE":
                self.handle_departure(event)
            elif event.type == "WAKEUP":
                self.try_schedule_departure(event.node_id, event.frame)
                
        return self.latencies

    def handle_arrival(self, event):
        frame = event.frame
        node_id = event.node_id
        
        if frame.stream_id not in self.routes:
            return # No route for this stream

        route = self.routes[frame.stream_id]
        
        # Check if we reached destination
        if frame.path_index >= len(route.path):
             return

        current_hop = route.path[frame.path_index]
        
        # Verify we are at the correct node
        if current_hop['node'] != node_id:
            return

        # If this is the last hop in the path, it's the destination
        if frame.path_index == len(route.path) - 1:
            latency = self.current_time - frame.creation_time
            self.latencies[frame.stream_id].append(latency)
            return

        # Not destination, enqueue for output
        out_port = current_hop['port']
        
        if (node_id, out_port) in self.port_schedulers:
            scheduler = self.port_schedulers[(node_id, out_port)]
            scheduler.enqueue(frame, self.current_time)
            self.try_schedule_departure(node_id, out_port)
        else:
            pass

    def try_schedule_departure(self, node_id, port):
        scheduler = self.port_schedulers[(node_id, port)]
        scheduler.advance_time(self.current_time)

        if self.current_time < scheduler.busy_until:
            return

        frame, priority = scheduler.get_next_frame(self.current_time)
        if frame:
            trans_time = scheduler.transmission_time(frame.size)
            scheduler.on_transmission_start(priority, self.current_time, trans_time)
            self.schedule_event(Event(self.current_time + trans_time, "DEPARTURE", frame, node_id))
            return

        next_time = scheduler.next_eligible_time(self.current_time)
        if next_time is not None and next_time > self.current_time:
            self.schedule_event(Event(next_time, "WAKEUP", port, node_id))

    def handle_departure(self, event):
        frame = event.frame
        node_id = event.node_id
        
        route = self.routes[frame.stream_id]
        current_hop = route.path[frame.path_index]
        out_port = current_hop['port']
        
        if out_port not in self.nodes[node_id].outgoing_links:
             return

        self.port_schedulers[(node_id, out_port)].on_transmission_end(self.current_time)
        link = self.nodes[node_id].outgoing_links[out_port]
        next_node_id = link.destination
        delay = link.delay
        
        frame.path_index += 1
        self.schedule_event(Event(self.current_time + delay, "ARRIVAL", frame, next_node_id))
        
        self.try_schedule_departure(node_id, out_port)
