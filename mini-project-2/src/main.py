import os
import argparse
from .loader import load_topology, load_streams, load_routes
from .simulation import Simulator
from .analysis import calculate_wcrt, calculate_wcrt_sp

def setup_output_logging(case_id, duration):
    import sys

    class Tee:
        def __init__(self, *files):
            self.files = files

        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()

        def flush(self):
            for f in self.files:
                f.flush()

    log_file = open(f"results/Case-{case_id}-{duration}.log", "w")
    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)
    
def main(case_id, duration):
    base_src_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_src_dir)
    test_case_dir = os.path.join(root_dir, f'testcases/test_case_{case_id}')
    
    topo_file = os.path.join(test_case_dir, 'topology.json')
    streams_file = os.path.join(test_case_dir, 'streams.json')
    routes_file = os.path.join(test_case_dir, 'routes.json')
    
    print("Loading configuration...")
    nodes, links = load_topology(topo_file)
    streams = load_streams(streams_file)
    routes = load_routes(routes_file)
    
    print(f"Loaded {len(nodes)} nodes, {len(links)} links, {len(streams)} streams.")


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
    
    ## 4. print and save result
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
    output_csv = f"results/Case-{case_id}-{duration}-WCRTs_Comparison.csv"
    # output_csv = os.path.join(test_case_dir, f'Case-{case_id}-WCRTs_Comparison.csv')
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
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", type=int)
    parser.add_argument("duration", type=float, nargs="?", default=2000000.0)
    args = parser.parse_args()
    
    duration = args.duration
    setup_output_logging(args.case_id, duration)
    
    print(f'------------ Start to execute case {args.case_id} ------------')
    main(args.case_id, duration)
    print(f'------------ Finish case {args.case_id} ------------')
