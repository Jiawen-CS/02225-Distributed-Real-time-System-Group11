## How to Run Mini Project 2

### 1. Requirements
- Python >= 3.10

Install the required dependencies in the project root directory:

```bash
pip install -r requirements.txt
```


### 2. Run the test case
```
cd mini-project-2
python -m src.main <case_id>
```
case_id specifies the test case:
- 1–3: normal cases
- 4: starvation cases

e.g
```
python -m src.main 1
```