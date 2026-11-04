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
RACE_PATH = re.compile(r"^/(\d{1,3})/(20\d{6})/(\d{1,2})/?$")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def get_links(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=25) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(html)
    return [urljoin(url, href) for href in parser.links]


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
            links = get_links(page)
        except Exception as exc:
            if page == BASE:
                raise RuntimeError(f"開催一覧の取得失敗: {exc}") from exc
            print(f"INDEX WARNING: {page}: {exc}", file=sys.stderr)
            continue

        for link in links:
            parsed = urlparse(link)
            if parsed.hostname not in ("keibure.com", "www.keibure.com"):
                continue

            match = RACE_PATH.fullmatch(parsed.path)
            if match and match.group(2) == TODAY:
                venue = int(match.group(1))
                race_no = int(match.group(3))
                if 1 <= race_no <= 12:
                    races[(venue, race_no)] = link.split("#")[0]
                continue

            if TODAY in link and link not in visited and link not in queue:
                queue.append(link)

    if not races:
        raise RuntimeError("ケイブレの当日開催リンクが見つかりません")

    return races


def main():
    print(f"Checking races for {TODAY}")
    races = discover()
    venues = len({venue for venue, _ in races})
    print(f"Discovered: {len(races)} links, {venues} venues")

    checked = 0
    errors = 0
    matches = []

    for (venue, race_no), url in sorted(races.items()):
        try:
            with redirect_stdout(io.StringIO()):
                matched = check_live_race(url)
            checked += 1
            if matched:
                matches.append((venue, race_no, url))
        except Exception as exc:
            errors += 1
            print(f"FETCH ERROR {url}: {type(exc).__name__}: {exc}")

    print("\n========== RESULTS ==========")
    print(f"Date: {TODAY}")
    print(f"Discovered venues: {venues}")
    print(f"Discovered races: {len(races)}")
    print(f"Checked: {checked}")
    print(f"Errors: {errors}")
    print(f"Matches: {len(matches)}")

    for venue, race_no, url in matches:
        print(f"Venue {venue} {race_no}R {url}")

    if errors:
        raise SystemExit(f"INCOMPLETE SCAN: {errors} race pages failed")


if __name__ == "__main__":
    main()
