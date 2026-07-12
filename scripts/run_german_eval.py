"""Batch-evaluate German anatomy questions against /rag/ask."""
import json
import sys
import urllib.request

QUESTIONS = [
    "Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammen und sortiere diese bitte nach Bewegungsrichtungen.",
    "Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, welche benötigt werden, um eine Faust zu schließen. Hierbei sollte die Innervation berücksichtigt werden. Bitte zeige mir dazu auch zwei didaktisch gute Bilder.",
    "Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und damit eine Enge unter dem Schulterdach?",
    "Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?",
    "Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktioniert?",
    "Gibt es den Vestibulookulären Reflex nur in der Horizontalen?",
    "Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?",
    "Bitte erkläre mir die Funktion des Herzens.",
    "Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürtel wo es um Bewegungen des Armes geht und Dinge wie Abduktion und Elevation.",
]

BASE = "http://127.0.0.1:8000/rag/ask"
DEFAULT_TIMEOUT = int(__import__("os").getenv("RAG_EVAL_TIMEOUT", "900"))


def ask(question: str, *, timeout: int = DEFAULT_TIMEOUT) -> dict:
    body = json.dumps({"question": question, "language": "de"}).encode("utf-8")
    req = urllib.request.Request(
        BASE,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    results = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {q[:60]}...", flush=True)
        try:
            data = ask(q)
            results.append({"question": q, "response": data, "error": None})
        except Exception as exc:
            results.append({"question": q, "response": None, "error": str(exc)})
    out = sys.argv[1] if len(sys.argv) > 1 else "german_eval_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
