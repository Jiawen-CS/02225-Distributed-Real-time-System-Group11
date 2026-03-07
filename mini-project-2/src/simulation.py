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
        
        # Calculate reservations per port per priority
        # Map: (node_id, port_id) -> {priority: bandwidth_fraction}
        reservations = {}
        
        for stream in streams:
            if stream.id not in routes:
                continue
            route = routes[stream.id]
            
            # Stream bandwidth in Mbps (bits / us)
            # size is bytes, period is us
            stream_bw = (stream.size * 8.0) / stream.period
            
            for hop in route.path:
                node_id = hop['node']
                port_id = hop['port']
                
                # End systems (port 0) or Switch ports
                # We need to find the link to get bandwidth
                if node_id in nodes and port_id in nodes[node_id].outgoing_links:
                    link = nodes[node_id].outgoing_links[port_id]
                    link_bw = link.bandwidth_mbps
                    
                    if (node_id, port_id) not in reservations:
                        reservations[(node_id, port_id)] = {}
                    
                    if stream.pcp not in reservations[(node_id, port_id)]:
                        reservations[(node_id, port_id)][stream.pcp] = 0.0
                    
                    # Add fraction
                    reservations[(node_id, port_id)][stream.pcp] += stream_bw / link_bw

        # Apply 75% Bandwidth Allocation Strategy (Match Analysis)
        AVB_LIMIT = 0.75
        for port_key, res in reservations.items():
            req_A = res.get(2, 0.0) # PCP 2 = Class A
            req_B = res.get(1, 0.0) # PCP 1 = Class B
            
            total_req = req_A + req_B
            
            if total_req > 0:
                # Distribute 75% proportionally
                res[2] = (req_A / total_req) * AVB_LIMIT
                res[1] = (req_B / total_req) * AVB_LIMIT
            else:
                res[2] = 0.0
                res[1] = 0.0

        for node_id, node in nodes.items():
            for port, link in node.outgoing_links.items():
                port_res = reservations.get((node_id, port), {})
                # We default to CBS mode as requested, but could be 'SP'
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
            scheduler.enqueue(frame)
            self.try_schedule_departure(node_id, out_port)
        else:
            pass

    def try_schedule_departure(self, node_id, port):
        scheduler = self.port_schedulers[(node_id, port)]
        if self.current_time < scheduler.busy_until:
            return

        frame, priority = scheduler.get_next_frame(self.current_time)
        if frame:
            # Notify scheduler of transmission start (for CBS credit update)
            scheduler.on_transmission_start(priority, frame.size, self.current_time)
            
            trans_time = scheduler.transmission_time(frame.size)
            scheduler.busy_until = self.current_time + trans_time
            self.schedule_event(Event(self.current_time + trans_time, "DEPARTURE", frame, node_id))

    def handle_departure(self, event):
        frame = event.frame
        node_id = event.node_id
        
        route = self.routes[frame.stream_id]
        current_hop = route.path[frame.path_index]
        out_port = current_hop['port']
        
        if out_port not in self.nodes[node_id].outgoing_links:
             return

        link = self.nodes[node_id].outgoing_links[out_port]
        next_node_id = link.destination
        delay = link.delay
        
        frame.path_index += 1
        self.schedule_event(Event(self.current_time + delay, "ARRIVAL", frame, next_node_id))
        
        self.try_schedule_departure(node_id, out_port)
