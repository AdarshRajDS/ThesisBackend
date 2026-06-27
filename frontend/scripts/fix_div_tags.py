"""Fix accidental </motion> tags in JSX files."""
import sys
from pathlib import Path

DIV = "div"
MOTION = "motion"

def fix(text: str) -> str:
    return text.replace(f"</{MOTION}>", f"</{DIV}>").replace(f"<{MOTION}", f"<{DIV}")


if __name__ == "__main__":
    for path in map(Path, sys.argv[1:]):
        original = path.read_text(encoding="utf-8")
        fixed = fix(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            print(f"fixed {path}")
