import csv
import sys
from collections import defaultdict

def matches(rows):
    if len(rows) != 7:
        return False

    numbers = {str(r["car_no"]).strip() for r in rows}
    if numbers != set("1234567"):
        return False

    lineup = rows[0]["lineup"].replace("・", "/").replace("-", "/").replace(" ", "")
    if lineup != "123/67/45":
        return False

    try:
        scores = {str(r["car_no"]).strip(): float(r["score"]) for r in rows}
    except (ValueError, KeyError):
        return False

    return scores["1"] > scores["6"] > scores["4"]

def main(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    required = {"race_id", "date", "venue", "race_no", "car_no", "score", "lineup"}
    if not rows or not required.issubset(rows[0].keys()):
        raise SystemExit("CSV columns missing")

    races = defaultdict(list)
    for row in rows:
        races[row["race_id"]].append(row)

    found = [r[0] for r in races.values() if matches(r)]
    print(f"Checked {len(races)} races; matched {len(found)}")

    for r in found:
        print(f'{r["date"]} {r["venue"]} {r["race_no"]}R: 123/67/45')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python keirin_filter.py races.csv")
    main(sys.argv[1])
