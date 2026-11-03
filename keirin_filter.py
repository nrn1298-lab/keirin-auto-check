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
    if __name__ == "__main__" and len(sys.argv) == 2:
    main(sys.argv[1])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage:


# 実際の競輪サイトから取得して判定
def check_live_race(url):
    import json
    import re
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    def get_array(name):
        pattern = r"(?:window\.)?" + re.escape(name) + r"\s*=\s*(\[)"
        match = re.search(pattern, html)
        if not match:
            raise ValueError(f"{name} not found")
        data, _ = json.JSONDecoder().raw_decode(html[match.start(1):])
        return data

    riders = get_array("__ents")
    lineup = get_array("__comp")

    if len(riders) != 7:
        return False

    groups = [str(x["cars"]).split("-") for x in lineup]
    print("Actual lineup:", " / ".join("-".join(g) for g in groups))

    if len(groups) != 3 or sorted(map(len, groups)) != [2, 2, 3]:
        return False

    if groups != [["1", "2", "3"], ["6", "7"], ["4", "5"]]:
        return False

    scores = {int(r["car_no"]): float(r["tokuten"]) for r in riders}
    print("Leader scores:", scores[1], scores[6], scores[4])

    return scores[1] > scores[6] > scores[4]


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--live":
    url = sys.argv[2]
    print("MATCH" if check_live_race(url) else "NOT MATCH")
