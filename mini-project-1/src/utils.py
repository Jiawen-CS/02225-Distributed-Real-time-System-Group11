from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "results.txt"



# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def log_only(*args, sep=" ", end="\n"):
    message = sep.join(str(a) for a in args) + end
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message)


def print_and_log(text=""):
    print(text)
    log_only(text)

