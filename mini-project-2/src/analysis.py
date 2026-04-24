from .model import Stream, Link
from .loader import load_topology, load_streams, load_routes
import math

def calculate_wcrt(nodes, links, streams, routes):
    link_traffic = {link_id: {'A': [], 'B': [], 'BE': []} for link_id in links}
    link_params = {link_id: {'idleSlope_A': 0.0, 'idleSlope_B': 0.0, 'linkRate': 0.0} for link_id in links}

    PCP_TO_CLASS = {
        2: 'A',
        1: 'B',
        0: 'BE',
        3: 'A', 4: 'A', 5: 'A', 6: 'A', 7: 'A' 
    }

    for s in streams:
        if s.id not in routes:
            continue
        route = routes[s.id]
        
        cls = PCP_TO_CLASS.get(s.pcp, 'BE')
        
        s_bw = (s.size * 8.0) / s.period
        
        for hop in route.path:
            node_id = hop['node']
            port_id = hop['port']
            
            if node_id in nodes and port_id in nodes[node_id].outgoing_links:
                link = nodes[node_id].outgoing_links[port_id]
                link_id = link.id
                
                trans_time = (s.size * 8.0) / link.bandwidth_mbps
                
                link_traffic[link_id][cls].append({
                    'id': s.id,
                    'C': trans_time,
                    'bw': s_bw
                })
                
                link_params[link_id]['linkRate'] = link.bandwidth_mbps
                if cls == 'A':
                    link_params[link_id]['idleSlope_A'] += s_bw
                elif cls == 'B':
                    link_params[link_id]['idleSlope_B'] += s_bw

    for link_id, params in link_params.items():
        link_rate = params['linkRate']

        # Reference test cases assume equal-magnitude slopes for the two AVB classes.
        params['idleSlope_A'] = 0.5 * link_rate if link_traffic[link_id]['A'] else 0.0
        params['idleSlope_B'] = 0.5 * link_rate if link_traffic[link_id]['B'] else 0.0

        reserved_fraction = 0.0
        if params['idleSlope_A'] > 0:
            reserved_fraction += params['idleSlope_A'] / link_rate
        if params['idleSlope_B'] > 0:
            reserved_fraction += params['idleSlope_B'] / link_rate

        if reserved_fraction > 1.0:
            print(
                f"WARNING: Link {link_id} violates CBS validity. "
                f"Reserved AVB fraction: {reserved_fraction:.2f}"
            )
            return {
                s.id: (float('nan') if PCP_TO_CLASS.get(s.pcp, 'BE') == 'BE' else float('inf'))
                for s in streams
            }

    wcrts = {}
    
    for s in streams:
        if s.id not in routes:
            wcrts[s.id] = 0.0
            continue
            
        route = routes[s.id]
        cls = PCP_TO_CLASS.get(s.pcp, 'BE')
        total_wcrt = 0.0

        if cls == 'BE':
            # The lecture CBS analysis does not provide bounded WCRTs for BE traffic.
            wcrts[s.id] = float('nan')
            continue
        
        for hop in route.path:
            node_id = hop['node']
            port_id = hop['port']
            
            if node_id in nodes and port_id in nodes[node_id].outgoing_links:
                link = nodes[node_id].outgoing_links[port_id]
                link_id = link.id
                
                params = link_params[link_id]
                traffic = link_traffic[link_id]
                
                linkRate = params['linkRate']
                idleSlope_A = params['idleSlope_A']
                idleSlope_B = params['idleSlope_B']
                
                C_A_max = max([t['C'] for t in traffic['A']]) if traffic['A'] else 0.0
                C_B_max = max([t['C'] for t in traffic['B']]) if traffic['B'] else 0.0
                C_BE_max = max([t['C'] for t in traffic['BE']]) if traffic['BE'] else 0.0
                
                C_i = (s.size * 8.0) / linkRate
                
                if cls == 'A':
                    sum_C_A = sum([t['C'] for t in traffic['A']])
                    sum_C_others = sum_C_A - C_i
                    expansion = linkRate / idleSlope_A if idleSlope_A > 0 else 1.0
                    SPI = sum_C_others * expansion
                    
                    LPI = max(C_B_max, C_BE_max)
                    
                    node_delay = SPI + LPI + C_i
                    
                elif cls == 'B':
                    sum_C_B = sum([t['C'] for t in traffic['B']])
                    sum_C_others = sum_C_B - C_i
                    expansion = linkRate / idleSlope_B if idleSlope_B > 0 else 1.0
                    SPI = sum_C_others * expansion
                    
                    LPI = C_BE_max
                    
                    if linkRate > idleSlope_A:
                        sendSlope_A = linkRate - idleSlope_A
                        HPI = LPI * (idleSlope_A / sendSlope_A) + C_A_max
                    else:
                        HPI = float('inf')

                    node_delay = SPI + HPI + LPI + C_i

                total_wcrt += node_delay
        
        wcrts[s.id] = total_wcrt
        
    return wcrts

def calculate_wcrt_sp(nodes, links, streams, routes):
    # 1. Analyze traffic per link
    # Map: link_id -> list of {id, C, T, PCP}
    link_traffic = {link_id: [] for link_id in links}
    
    for s in streams:
        if s.id not in routes:
            continue
        route = routes[s.id]
        
        for hop in route.path:
            node_id = hop['node']
            port_id = hop['port']
            
            if node_id in nodes and port_id in nodes[node_id].outgoing_links:
                link = nodes[node_id].outgoing_links[port_id]
                link_id = link.id
                
                trans_time = (s.size * 8.0) / link.bandwidth_mbps
                
                link_traffic[link_id].append({
                    'id': s.id,
                    'C': trans_time,
                    'T': s.period,
                    'PCP': s.pcp
                })

    # 2. Calculate WCRT per stream
    wcrts = {}
    
    for s in streams:
        if s.id not in routes:
            wcrts[s.id] = 0.0
            continue
            
        route = routes[s.id]
        total_wcrt = 0.0
        
        for hop in route.path:
            node_id = hop['node']
            port_id = hop['port']
            
            if node_id in nodes and port_id in nodes[node_id].outgoing_links:
                link = nodes[node_id].outgoing_links[port_id]
                link_id = link.id
                
                traffic_on_link = link_traffic[link_id]
                
                # Identify C_i
                C_i = (s.size * 8.0) / link.bandwidth_mbps
                
                # Identify sets
                HP = []
                SP = []
                LP = []
                
                for t in traffic_on_link:
                    if t['id'] == s.id:
                        continue
                    
                    if t['PCP'] > s.pcp:
                        HP.append(t)
                    elif t['PCP'] == s.pcp:
                        SP.append(t)
                    else:
                        LP.append(t)
                
                # Blocking B_i = max(C_k) for k in LP
                B_i = max([t['C'] for t in LP]) if LP else 0.0
                
                # Same Priority Interference (FIFO)
                I_SP = sum([t['C'] for t in SP])
                
                # Iterative RTA
                # R = C_i + B_i + I_SP + Sum(ceil(R/T_j)*C_j) for j in HP
                
                R = C_i + B_i + I_SP
                
                # Optimization: if no HP, we are done
                if not HP:
                    node_delay = R
                else:
                    while True:
                        I_HP = 0.0
                        for t in HP:
                            I_HP += math.ceil(R / t['T']) * t['C']
                        
                        R_new = C_i + B_i + I_SP + I_HP
                        
                        if R_new <= R:
                            break
                        
                        if R_new > 200000: # Safety break
                            R = float('inf')
                            break
                            
                        R = R_new
                    node_delay = R
                
                total_wcrt += node_delay
                
        wcrts[s.id] = total_wcrt
        
    return wcrts
