## How to Run Mini Project 2

### 1. Requirements
- Python >= 3.10

Install the required dependencies in the `mini-project-2` directory:

```bash
pip install -r requirements.txt
```


### 2. How to Run
Run from the `mini-project-2` directory:

```bash
cd mini-project-2
python -m src.main <case_id> [duration]
```

- `case_id` specifies the test case:
- 1–3: normal cases
- 4: starvation of SP case
- `duration` is the simulation time in microseconds.
- If `duration` is not provided, the default value is `2000000.0`.

Examples:

```bash
python -m src.main 1
python -m src.main 1 2000000.0
python -m src.main 4 4000000.0
```

### 3. How to get the result
The program writes the following output files to the `results/` folder:

- Log file:
  `results/Case-<case_id>-<duration>.log`
- CSV summary:
  `results/Case-<case_id>-<duration>-WCRTs_Comparison.csv`

For example:

```text
results/Case-1-2000000.0.log
results/Case-1-2000000.0-WCRTs_Comparison.csv
```

The log file contains the full terminal output, and the CSV file contains the latency comparison between simulation and analysis.
