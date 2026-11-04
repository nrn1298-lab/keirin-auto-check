import io
import re
import sys
from contextlib import redirect_stdout
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from keirin_filter import check_live_race

BASE = "https://www.keibure.com/"
TODAY = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")
RACE_RE = re.compile(r"^/(\d{1,3})/(20\d{6})/(\d{1,2})/?$")
HTML_RACE_RE = re.compile(
    r"(?:https?://(?:www\.)?keibure\.com)?/\d{1,3}/20\d{6}/\d{1,2}(?:[/?#][^\s\"'<>]*)?"
)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

def fetch(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")

def discover():
    queue = [BASE]
    visited = set()
    races = {}

    while queue and len(visited) < 40:
        page = queue.pop(0)
        if page in visited:
            continue
        visited.add(page)

        try:
            html = fetch(page)
        except Exception as exc:
            if page == BASE:
                raise RuntimeError(f"開催一覧の取得失敗: {exc}") from exc
            print(f"INDEX WARNING: {page}: {exc}")
            continue

        parser = Links()
        parser.feed(html)
        candidates = parser.links + HTML_RACE_RE.findall(html)

        for candidate in candidates:
            url = urljoin(page, candidate).split("#", 1)[0]
            parsed = urlparse(url)
            if parsed.hostname not in ("keibure.com", "www.keibure.com"):
                continue

            match = RACE_RE.fullmatch(parsed.path)
            if match and match.group(2) == TODAY:
                venue = int(match.group(1))
                race_no = int(match.group(3))
                if 1 <= race_no <= 12:
                    races[(venue, race_no)] = (
                        f"https://www.keibure.com/{venue}/{TODAY}/{race_no}"
                    )
            elif TODAY in url and url not in visited and url not in queue:
                queue.append(url)

    if not races:
        raise RuntimeError("ケイブレの当日レースURLが見つかりません")
    return races

def main():
    print(f"Checking races for {TODAY}")
    races = discover()
    print(f"Discovered: {len(races)} race URLs")

    checked = 0
    missing_data = []
    errors = []
    matches = []

    for (venue, race_no), url in sorted(races.items()):
        try:
            with redirect_stdout(io.StringIO()):
                matched = check_live_race(url)
            checked += 1
            if matched:
                matches.append((venue, race_no, url))
        except ValueError as exc:
            if "__ents not found" in str(exc):
                missing_data.append(url)
            else:
                errors.append(f"{url}: {exc}")
        except Exception as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")

    print("\n========== RESULTS ==========")
    print(f"Date: {TODAY}")
    print(f"Discovered venues: {len(set(v for v, _ in races))}")
    print(f"Discovered URLs: {len(races)}")
    print(f"Checked: {checked}")
    print(f"Pages without rider data: {len(missing_data)}")
    print(f"Other errors: {len(errors)}")
    print(f"Matches: {len(matches)}")

    for venue, race_no, url in matches:
        print(f"MATCH: Venue {venue} {race_no}R {url}")

    for url in missing_data:
        print(f"NO RIDER DATA: {url}")

    for error in errors:
        print(f"FETCH ERROR: {error}")

    if missing_data or errors:
        raise SystemExit(
            f"INCOMPLETE SCAN: {len(missing_data)} pages without rider data, "
            f"{len(errors)} other errors"
        )

if __name__ == "__main__":
    main()
