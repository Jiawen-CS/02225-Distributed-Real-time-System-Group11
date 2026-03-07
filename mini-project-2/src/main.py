import os
from loader import load_topology, load_streams, load_routes
from simulation import Simulator
from analysis import calculate_wcrt, calculate_wcrt_sp

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_case_dir = os.path.join(base_dir, 'testcases/test-case-1')
    
    topo_file = os.path.join(test_case_dir, 'topology.json')
    streams_file = os.path.join(test_case_dir, 'streams.json')
    routes_file = os.path.join(test_case_dir, 'routes.json')
    
    print("Loading configuration...")
    nodes, links = load_topology(topo_file)
    streams = load_streams(streams_file)
    routes = load_routes(routes_file)
    
    print(f"Loaded {len(nodes)} nodes, {len(links)} links, {len(streams)} streams.")
    
    duration = 20000.0 

    # 1. Run Simulation (CBS Mode)
    print(f"Starting CBS simulation for {duration} us...")
    sim_cbs = Simulator(nodes, links, streams, routes, mode='CBS')
    latencies_cbs = sim_cbs.run(duration)
    
    # 2. Run Simulation (SP Mode)
    print(f"Starting SP simulation for {duration} us...")
    sim_sp = Simulator(nodes, links, streams, routes, mode='SP')
    latencies_sp = sim_sp.run(duration)

    # 3. Run Analysis
    print("Running WCRT Analysis (CBS)...")
    analytical_wcrts_cbs = calculate_wcrt(nodes, links, streams, routes)
    
    print("Running WCRT Analysis (SP)...")
    analytical_wcrts_sp = calculate_wcrt_sp(nodes, links, streams, routes)
    
    print("\nComparison Results (End-to-End Latency in us):")
    print(f"{'Stream ID':<10} {'PCP':<5} {'Sim(CBS)':<10} {'Sim(SP)':<10} {'Ana(CBS)':<10} {'Ana(SP)':<10}")
    
    for stream in streams:
        sid = stream.id
        
        lats_cbs = latencies_cbs.get(sid, [])
        max_cbs = max(lats_cbs) if lats_cbs else 0.0
        
        lats_sp = latencies_sp.get(sid, [])
        max_sp = max(lats_sp) if lats_sp else 0.0
        
        ana_cbs = analytical_wcrts_cbs.get(sid, 0.0)
        ana_sp = analytical_wcrts_sp.get(sid, 0.0)
        
        print(f"{sid:<10} {stream.pcp:<5} {max_cbs:<10.2f} {max_sp:<10.2f} {ana_cbs:<10.2f} {ana_sp:<10.2f}")

    # 4. Save to CSV
    output_csv = os.path.join(test_case_dir, 'WCRTs_Comparison.csv')
    with open(output_csv, 'w') as f:
        f.write("StreamID,PCP,SimMax_CBS,SimMax_SP,AnaWCRT_CBS,AnaWCRT_SP\n")
        for stream in streams:
            sid = stream.id
            lats_cbs = latencies_cbs.get(sid, [])
            max_cbs = max(lats_cbs) if lats_cbs else 0.0
            
            lats_sp = latencies_sp.get(sid, [])
            max_sp = max(lats_sp) if lats_sp else 0.0
            
            ana_cbs = analytical_wcrts_cbs.get(sid, 0.0)
            ana_sp = analytical_wcrts_sp.get(sid, 0.0)
            
            f.write(f"{sid},{stream.pcp},{max_cbs},{max_sp},{ana_cbs},{ana_sp}\n")
    print(f"\nResults saved to {output_csv}")

if __name__ == "__main__":
    main()
