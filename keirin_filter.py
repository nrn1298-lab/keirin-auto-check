import csv
import json
import re
import sys
from collections import defaultdict
from urllib.request import Request, urlopen

TARGET_LINEUP = [["1", "2", "3"], ["6", "7"], ["4", "5"]]


def normalize_groups(value):
    if isinstance(value, str):
        value = value.strip()
        value = re.sub(r"[・／|\s]+", "/", value)
        value = value.replace("－", "-").replace("−", "-")
        parts = [p for p in value.split("/") if p]
        return [[c for c in re.findall(r"[1-7]", part)] for part in parts]
    groups = []
    for item in value:
        cars = item.get("cars", "") if isinstance(item, dict) else item
        if isinstance(cars, list):
            groups.append([str(c).strip() for c in cars])
        else:
            groups.append(re.findall(r"[1-7]", str(cars)))
    return groups


def converted_lineup(groups, scores):
    if len(groups) != 3 or list(map(len, groups)) != [3, 2, 2]:
        return None
    cars = [car for group in groups for car in group]
    if len(cars) != 7 or set(cars) != set("1234567"):
        return None
    try:
        leaders = [float(scores[group[0]]) for group in groups]
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    if len(set(leaders)) != 3:
        return None
    ranked = sorted(range(3), key=lambda i: leaders[i], reverse=True)
    if len(groups[ranked[0]]) != 3:
        return None
    labels = {}
    for rank, index in enumerate(ranked):
        labels[index] = (["1", "2", "3"] if rank == 0 else
                         ["4", "5"] if rank == 1 else ["6", "7"])
    return [labels[i] for i in range(3)]


def matches(rows):
    if len(rows) != 7:
        return False
    try:
        scores = {str(r["car_no"]).strip(): float(r["score"]) for r in rows}
        groups = normalize_groups(rows[0]["lineup"])
    except (KeyError, ValueError, TypeError):
        return False
    return converted_lineup(groups, scores) == TARGET_LINEUP


def check_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"race_id", "date", "venue", "race_no", "car_no", "score", "lineup"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit("CSV columns missing")
    races = defaultdict(list)
    for row in rows:
        races[row["race_id"]].append(row)
    found = [race[0] for race in races.values() if matches(race)]
    print(f"Checked {len(races)} races; matched {len(found)}")
    for row in found:
        print(f'{row["date"]} {row["venue"]} {row["race_no"]}R: 123/67/45')


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
    try:
        scores = {str(r["car_no"]).strip(): float(r["tokuten"]) for r in riders}
    except (KeyError, ValueError, TypeError):
        print("NOT MATCH: missing scores")
        return False
    groups = normalize_groups(lineup)
    print("Actual lineup:", " / ".join("".join(g) for g in groups))
    converted = converted_lineup(groups, scores)
    print("Converted lineup:", " / ".join("".join(g) for g in converted) if converted else "invalid")
    return converted == TARGET_LINEUP


def main():
    if len(sys.argv) == 2 and sys.argv[1] != "--live":
        check_csv(sys.argv[1])
    elif len(sys.argv) == 3 and sys.argv[1] == "--live":
        result = check_live_race(sys.argv[2])
        print("MATCH" if result else "NOT MATCH")
    else:
        raise SystemExit("Usage: python keirin_filter.py races.csv OR python keirin_filter.py --live URL")


if __name__ == "__main__":
    main()
