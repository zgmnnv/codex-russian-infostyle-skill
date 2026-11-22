#!/usr/bin/env python3
"""Aggregate semantic reviews of responses to infostyle test cases."""

import argparse
import hashlib
import json
import re
from pathlib import Path

CRITERIA = ("facts", "meaning", "reader", "delivery")
CASES = Path(__file__).with_name("test-cases.md")


def review(path: Path, known_cases: set[str]) -> tuple[str, str]:
    if path.stem not in known_cases:
        return "ERROR", "нет такого задания в test-cases.md"
    answer = path.read_bytes()
    if not answer.decode("utf-8").strip():
        return "FAIL", "пустой ответ"

    digest = hashlib.sha256(answer).hexdigest()
    record = path.with_suffix(".review.json")
    if not record.exists():
        return "REVIEW", f"нет оценки, sha256={digest}"
    data = json.loads(record.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return "ERROR", "ожидается объект JSON"
    if data.get("sha256") != digest:
        return "REVIEW", f"нужна оценка текущего ответа, sha256={digest}"
    if any(data.get(key) not in ("PASS", "FAIL") for key in CRITERIA):
        return "ERROR", "нужны четыре оценки PASS или FAIL"
    note = data.get("note")
    if not isinstance(note, str) or not note.strip():
        return "ERROR", "нет обоснования"
    failed = [key for key in CRITERIA if data[key] == "FAIL"]
    if failed:
        return "FAIL", f"{', '.join(failed)} — {note}"
    return "PASS", note


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="каталог ответов или один caseN.md")
    path = parser.parse_args().path
    ids = re.findall(r"^### Кейс (\d+):", CASES.read_text(encoding="utf-8"), re.M)
    known = {f"case{number}" for number in ids}

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.glob("case*.md"))
    else:
        parser.error("путь не найден")
    if not files:
        parser.error("нет ответов caseN.md")

    passed = 0
    incomplete = False
    for file in files:
        try:
            if file.suffix != ".md":
                status, detail = "ERROR", "ожидается файл caseN.md"
            else:
                status, detail = review(file, known)
        except (OSError, ValueError) as error:
            status, detail = "ERROR", str(error)
        print(f"{file.stem}: {status} — {detail}")
        passed += status == "PASS"
        incomplete |= status in ("REVIEW", "ERROR")

    print(f"Ответов в прогоне: {len(files)}. Заданий в наборе: {len(known)}.")
    if incomplete:
        print("Оценка не завершена.")
        return 2
    print(f"PASS: {passed}/{len(files)}. Score: {passed / len(files) * 100:.1f}%")
    return 0 if passed == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
