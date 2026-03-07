import json
import os

def calculate_avb_load(streams_file):
    with open(streams_file, 'r') as f:
        data = json.load(f)
        
    streams = data.get('streams', [])
    
    total_avb_load = 0.0
    max_class_a_size = 0
    max_be_size = 0
    
    print(f"Analyzing {streams_file}...")
    
    for stream in streams:
        pcp = stream.get('PCP')
        size = stream.get('size')
        period = stream.get('period')
        
        # Bandwidth in Mbps
        bw = (size * 8.0) / period
        
        if pcp == 2: # Class A
            total_avb_load += bw
            if size > max_class_a_size:
                max_class_a_size = size
        elif pcp == 1: # Class B
            total_avb_load += bw
        elif pcp == 0: # BE
            if size > max_be_size:
                max_be_size = size
                
    print(f"  Total AVB Load: {total_avb_load:.2f} Mbps")
    print(f"  Max Class A Size: {max_class_a_size} Bytes")
    print(f"  Max BE Size: {max_be_size} Bytes")
    print("-" * 30)

def main():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(curr_dir)
    root_dir = os.path.dirname(src_dir)
    test_case_dir = os.path.join(root_dir, 'testcases/')
    
    # List of test case directories
    test_cases = ['test_case_1', 'test_case_2', 'test_case_3']
    
    for case in test_cases:
        streams_file = os.path.join(test_case_dir, case, 'streams.json')
        if os.path.exists(streams_file):
            calculate_avb_load(streams_file)
        else:
            print(f"File not found: {streams_file}")

if __name__ == "__main__":
    main()
