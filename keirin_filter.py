import csv
import json
import re
import sys
from collections import defaultdict
from urllib.request import Request, urlopen


TARGET_LINEUP = [["1", "2", "3"], ["6", "7"], ["4", "5"]]


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


def check_csv(path):
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


def extract_array(html, name):
    pattern = r"(?:window\.)?" + re.escape(name) + r"\s*=\s*(\[)"
    match = re.search(pattern, html)
    if not match:
        raise ValueError(f"{name} not found")

    data, _ = json.JSONDecoder().raw_decode(html[match.start(1):])
    if not isinstance(data, list):
        raise ValueError(f"{name} is not an array")
    return data


def check_live_race(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    riders = extract_array(html, "__ents")
    lineup = extract_array(html, "__comp")

    if len(riders) != 7:
        print("NOT MATCH: not a 7-rider race")
        return False

    numbers = {str(r["car_no"]) for r in riders}
    if numbers != set("1234567"):
        print("NOT MATCH: invalid car numbers")
        return False

    groups = [str(x["cars"]).split("-") for x in lineup]
    print("Actual lineup:", " / ".join("-".join(g) for g in groups))

    if groups != TARGET_LINEUP:
        return False

    scores = {str(r["car_no"]): float(r["tokuten"]) for r in riders}
    print("Leader scores:", scores["1"], scores["6"], scores["4"])

    return scores["1"] > scores["6"] > scores["4"]


def main():
    if len(sys.argv) == 2 and sys.argv[1] != "--live":
        check_csv(sys.argv[1])
    elif len(sys.argv) == 3 and sys.argv[1] == "--live":
        result = check_live_race(sys.argv[2])
        print("MATCH" if result else "NOT MATCH")
    else:
        raise SystemExit(
            "Usage: python keirin_filter.py races.csv OR "
            "python keirin_filter.py --live URL"
        )


if __name__ == "__main__":
    main()
