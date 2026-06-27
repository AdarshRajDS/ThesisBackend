import os
from src.assessment.run_annotation_check import run_annotation_grading

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def grade_annotation(file):

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    raw_result = run_annotation_grading(file_path)

    # 🔥 If your grader returns a STRING → convert to structured format
    if isinstance(raw_result, str):
        return {
            "score": None,
            "feedback": raw_result,
            "missing_structures": []
        }

    # 🔥 If your grader already returns a dict → pass through safely
    return {
        "score": raw_result.get("score"),
        "feedback": raw_result.get("feedback", ""),
        "missing_structures": raw_result.get("missing_structures", [])
    }
