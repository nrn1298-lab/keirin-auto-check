from datetime import datetime
from zoneinfo import ZoneInfo
from keirin_filter import check_live_race

VENUES = {
    "青森": (12, 12),
    "大宮": (25, 12),
    "豊橋": (45, 12),
    "取手": (23, 7),
    "別府": (86, 11),
}

date = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")
checked = 0
failed = 0
matches = []

print(f"Checking races for {date}")

for name, (code, count) in VENUES.items():
    for race_no in range(1, count + 1):
        url = f"https://www.keibure.com/{code}/{date}/{race_no}"
        print(f"\n{name} {race_no}R")

        try:
            result = check_live_race(url)
            checked += 1
            if result:
                matches.append((name, race_no, url))
                print(">>> MATCH FOUND")
        except Exception as e:
            failed += 1
            print(f"FETCH ERROR: {type(e).__name__}: {e}")

print("\n========== RESULTS ==========")
print(f"Date: {date}")
print(f"Checked: {checked}")
print(f"Errors: {failed}")
print(f"Matches: {len(matches)}")

for name, race_no, url in matches:
    print(f"{name} {race_no}R {url}")

if failed:
    raise SystemExit(f"INCOMPLETE SCAN: {failed} races could not be checked")
