## How to Run Mini Project 2

### 1. Requirements
- Python >= 3.10

Install the required dependencies in the project root directory:

```bash
pip install -r requirements.txt
```


### 2. Run the test case
```
python -m src.main <case_id>
```
case_id specifies the test case:
- 1–3: normal cases
- 4: starvation cases

e.g
```
python -m src.main 1
```

### 3. How to get the result
1. The log file is generated from the terminal output.
2. The WCRT results are stored in the corresponding test case folders.

And we have put them into resutls folder.